# ClaimSense AI — Operational Runbook

**Version:** 1.0  
**Engagement:** Forward Deployed Engineer (FDE) Capstone — Handover  
**Target Audience:** Operations Engineers, DevOps, Compliance Officers, and Lead Adjusters  
**Applicability:** Production ECS Fargate, Staging, and Local Emulation  
**Status:** Certified & Verified

---

## Overview

This runbook documents the four standard operating procedures required to maintain, operate, and troubleshoot the ClaimSense AI motor claims adjudication co-pilot:

1. [Procedure 1: Add a User with Role & Claim Entitlements](#procedure-1-add-a-user-with-role--claim-entitlements)
2. [Procedure 2: Roll Back a Deployment (Canary / Blue-Green / Git)](#procedure-2-roll-back-a-deployment)
3. [Procedure 3: Escalate a Flagged Claim Manually (SIU Referral)](#procedure-3-escalate-a-flagged-claim-manually)
4. [Procedure 4: Update the Policy Corpus & Grounded Index](#procedure-4-update-the-policy-corpus)

---

## Procedure 1: Add a User with Role & Claim Entitlements

### Context & Policy
In accordance with ADR-011 and ADR-012, all user authorization is evaluated in deterministic code ahead of any agent instantiation. Every caller must possess an HMAC-SHA256 cryptographically signed Bearer token containing their unique subject (`sub`), enterprise role (`role`), and entitled claim IDs (`claims`).

### Step-by-Step Execution

#### Step 1: Determine User Attributes
- **User Identifier (`sub`):** e.g. `adjuster-marcus`
- **Enterprise Role (`role`):** One of `licensed_adjuster`, `senior_adjuster`, `siu_investigator`, `compliance_auditor`
- **Claim Entitlements (`claims`):**
  - Full portfolio: `["*"]`
  - Territory/Caseload restricted: e.g. `["CLM-2026-0150", "CLM-2026-0151", "CLM-2026-0152"]`
- **Time To Live (`ttl_seconds`):** Default `86400` (24 hours)

#### Step 2: Generate Signed Cryptographic Token
Run the built-in CLI utility to issue a signed token:
```bash
python3 -c "
from src.spine.security import TokenManager
token = TokenManager.create_signed_token(
    user_id='adjuster-marcus',
    role='licensed_adjuster',
    entitled_claims=['CLM-2026-0150', 'CLM-2026-0151'],
    ttl_seconds=86400 * 30
)
print('Bearer Token:', token)
"
```

#### Step 3: Verify Token Authenticity
Verify that the token can successfully query the API boundary:
```bash
curl -i -H "Authorization: Bearer <TOKEN_OUTPUT>" http://localhost:8000/claims/CLM-2026-0150
```
- **Expected Result:** `HTTP/1.1 200 OK`
- **Refusal Verification:**
  ```bash
  curl -i -H "Authorization: Bearer <TOKEN_OUTPUT>" http://localhost:8000/claims/CLM-2026-0101
  ```
- **Expected Result:** `HTTP/1.1 403 Forbidden` with `"Access denied"` detail and zero claim data leaked.

#### Step 4: Verify Audit Trail Entry
Confirm that the access attempt was recorded:
```bash
curl -H "Authorization: Bearer token-admin-access" http://localhost:8000/audit-trail?limit=1
```

---

## Procedure 2: Roll Back a Deployment

### Trigger Conditions
- CloudWatch Alarm `HighLatencyP95Alarm` breached (> 60,000 ms SLA)
- CloudWatch Alarm `HighErrorRateAlarm` breached (> 5.0% error rate)
- Evaluation gate regression detected during canary release

### Step-by-Step Rollback Execution

#### Option A: Production AWS ECS Fargate Rollback (Zero-Downtime)
1. List previous stable task definition revisions:
   ```bash
   aws ecs describe-task-definition --task-definition claimsense-ai-production
   ```
2. Update the ECS Service to point to the known stable revision (e.g. revision `14`):
   ```bash
   aws ecs update-service \
     --cluster claimsense-ai-cluster \
     --service claimsense-ai-service \
     --task-definition claimsense-ai-production:14 \
     --force-new-deployment
   ```
3. Wait for service stability:
   ```bash
   aws ecs wait services-stable \
     --cluster claimsense-ai-cluster \
     --services claimsense-ai-service
   ```

#### Option B: Git Commit Revert & CI Deployment
1. Identify the offending commit hash:
   ```bash
   git log -n 5 --oneline
   ```
2. Revert the commit and push:
   ```bash
   git revert <BAD_COMMIT_HASH> -m 1
   git push origin main
   ```
3. The GitHub Actions CI pipeline (`.github/workflows/ci.yml`) will automatically validate the evaluation gate and deploy the restored image.

#### Step 3: Verification & Recovery Sign-Off
1. Verify public health check:
   ```bash
   curl -f http://localhost:8000/health
   # Expected: {"status": "healthy", "service": "ClaimSense AI", ...}
   ```
2. Query telemetry metrics to confirm alarm state returned to `OK`:
   ```bash
   curl http://localhost:8000/dashboard/metrics | jq .alarm_status
   # Expected: "OK"
   ```

---

## Procedure 3: Escalate a Flagged Claim Manually (SIU Referral)

### Context & Policy
When the AI co-pilot or a licensed adjuster flags a claim for fraud indicators (`flag`), narrative contradictions, or suspicious timing, the claim must be escalated to the Special Investigation Unit (SIU) with all supporting evidence frozen.

### Step-by-Step Execution

#### Step 1: Review Flagged AI Dossier
Query the claim adjudication outcome and identified contradictions:
```bash
curl -H "Authorization: Bearer token-jane-full-access" \
     -X POST http://localhost:8000/adjudicate \
     -H "Content-Type: application/json" \
     -d '{"claim_id": "CLM-2026-0111"}'
```

#### Step 2: Formulate Adjuster Confirmation & Escalation Payload
Prepare the idempotent CMS write-back payload with `decision: "flag"` and `override_reason` detailing the SIU referral:
```bash
IDEMPOTENCY_KEY=$(uuidgen)

curl -X POST http://localhost:8000/claims/CLM-2026-0111/decisions \
  -H "Authorization: Bearer token-jane-full-access" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -d '{
    "idempotency_key": "'"$IDEMPOTENCY_KEY"'",
    "claim_id": "CLM-2026-0111",
    "decision": "flag",
    "decision_detail": "fraud",
    "adjuster_id": "adjuster-jane",
    "reasoning": "Claim escalated to SIU. Physical impact inconsistencies detected between police report and repair shop appraisal.",
    "cited_clauses": ["CLS-PER-001", "CLS-COV-001"],
    "payout_authorized": 0.0
  }'
```

#### Step 3: Verify Idempotent CMS Confirmation
- **Status:** `HTTP/1.1 201 Created`
- Verify that `idempotent_replay: false` on first submission.
- Re-running the identical command yields `HTTP/1.1 200 OK` with `idempotent_replay: true`.

#### Step 4: Reassign in CMS to SIU Queue
Update the claim record in the CMS system of record:
```bash
# In client CMS REST API:
# PUT /claims/CLM-2026-0111/assignment
# {"assigned_team": "SIU_TIER_2", "priority": "HIGH", "lock_payout": true}
```

---

## Procedure 4: Update the Policy Corpus & Grounded Index

### Context
When underwriting issues new policy endorsements or updates clause wording (e.g., introducing a new Electronic Vehicle Battery Warranty clause `CLS-COV-015`), the policy corpus must be updated without restarting the cluster or hallucinating ungrounded citations.

### Step-by-Step Execution

#### Step 1: Draft the Canonical Clause Specification
Open `src/contracts/policyadmin.py` or the canonical clause catalog and append the new clause:
```json
{
  "clause_id": "CLS-COV-015",
  "title": "Electric Vehicle High-Voltage Battery Coverage",
  "section": "Coverage",
  "text": "We will cover accidental thermal runaway or impact damage to the high-voltage traction battery pack resulting from a covered road hazard.",
  "applies_to_coverage": ["Comprehensive"]
}
```

#### Step 2: Validate Clause Taxonomy Format
Verify that the new clause identifier matches the required regex pattern:
```bash
python3 -c "
import re
pattern = re.compile(r'^CLS-[A-Z]{3}-[0-9]{3}$')
assert pattern.match('CLS-COV-015'), 'Invalid format'
print('Clause format valid!')
"
```

#### Step 3: Rebuild the In-Memory BM25 Index
Execute the retrieval index test to verify index ingestion and query ranking:
```bash
PYTHONPATH=. pytest tests/test_retrieval.py -v
```

#### Step 4: Verify Citation Grounding Gate
Run the citation grounding validation test:
```bash
python3 -c "
from src.retrieval.policy_index import PolicyClauseIndex
idx = PolicyClauseIndex()
results = idx.search('EV battery pack damage from road debris', top_k=3)
print('Retrieved clauses:', [c.clause_id for c in results])
valid, invalid = idx.validate_citations([c.clause_id for c in results])
assert len(invalid) == 0, f'Ungrounded citations found: {invalid}'
print('Citation grounding verified!')
"
```

#### Step 5: Run Evaluation Suite Gate
Before shipping the updated corpus to production, execute the full evaluation suite to ensure no regressions across the 150 standard and adversarial cases:
```bash
python3 evals/run_evals.py
```
- **Pass Criterion:** 100% schema validation, 0 duplicate IDs.
