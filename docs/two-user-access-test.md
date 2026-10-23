# ClaimSense AI — Milestone 4 Two-User Access Control Test Evidence

**Document Version:** 1.0  
**Engagement Week:** Milestone 4 (Week 4)  
**Date of Execution:** 23 October 2026  
**Target Motor Claim:** `CLM-2026-0101` (Claimant: Sarah Chen, Rear-end collision, Damage: $2,800.00, Deductible: $500.00)  
**Evaluator Reference:** Area D Rubric (Weight: 20 Points) — Strong Criteria:  
> *"Authorisation is enforced in code ahead of any agent, holds on every route, and every call is recorded with user, action and resource, including refusals."*

---

## 1. Test Setup & Persona Mapping

To conclusively demonstrate that access control is enforced in deterministic code prior to any agent instantiation, two distinct adjuster personas were subjected to identical requests against the exact same motor claim (`CLM-2026-0101`):

| Persona Attribute | User 1 (Authorized Adjuster) | User 2 (Unauthorized Adjuster) |
|---|---|---|
| **Identity (`sub`)** | `adjuster-jane` | `adjuster-bob` |
| **Enterprise Role** | `licensed_adjuster` | `licensed_adjuster` |
| **Authentication Credential** | `Bearer token-jane-full-access` | `Bearer token-bob-limited-access` |
| **Claim Entitlements** | `["*"]` (Global portfolio license) | `["CLM-2026-0104", "CLM-2026-0109", "CLM-2026-0113"]` |
| **Target Claim Entitlement** | **ENTITLED** to `CLM-2026-0101` | **NOT ENTITLED** to `CLM-2026-0101` |
| **Expected HTTP Status** | `200 OK` | `403 Forbidden` |
| **Data Leakage Allowed** | Full Claim Dossier & Draft | **ZERO Claim/Policy/Agent Data** |
| **Audit Outcome** | `granted` | `denied` |

---

## 2. Test Execution 1: Adjudication Pipeline (`POST /adjudicate`)

The `/adjudicate` endpoint triggers the 4-agent collaborative pipeline (`FileReaderAgent`, `CoverageAgent`, `RiskAssessmentAgent`, `DecisionDraftAgent`) bounded by the deterministic spine.

### User 1 (Authorized: Jane) — Request & Response

#### User 1 Request:
```http
POST /adjudicate HTTP/1.1
Host: api.claimsense.internal
Authorization: Bearer token-jane-full-access
Content-Type: application/json

{
  "claim_id": "CLM-2026-0101"
}
```

#### User 1 Response:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "claim_id": "CLM-2026-0101",
  "decision": "approve",
  "decision_detail": "standard_approval",
  "reasoning": "Collision damage verified and covered under policy terms. Rear impact confirmed consistent with traffic light stoppage. Deductible of $500 applied to $2,800 repair estimate.",
  "cited_clauses": [
    "CLS-PER-001",
    "CLS-COV-001"
  ],
  "payout_authorized": 2300.0,
  "verdict_source": "model_agent",
  "spine_facts": {
    "policy_in_force": true,
    "days_past_expiry": 0,
    "vehicle_scheduled": true,
    "repair_to_value_ratio": 0.1,
    "is_constructive_total_loss": false,
    "applicable_deductible": 500.0
  },
  "requires_human_confirmation": true
}
```

---

### User 2 (Unauthorized: Bob) — Request & Response

#### User 2 Request:
```http
POST /adjudicate HTTP/1.1
Host: api.claimsense.internal
Authorization: Bearer token-bob-limited-access
Content-Type: application/json

{
  "claim_id": "CLM-2026-0101"
}
```

#### User 2 Response:
```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "detail": "Access denied: User 'adjuster-bob' is not entitled to claim 'CLM-2026-0101'"
}
```

> [!IMPORTANT]
> **Zero Data Leakage Verification:** Notice that User 2 received **no** claimant name, **no** vehicle details, **no** loss description, **no** financial figures, and **no** model reasoning. The rejection was executed in deterministic code *before* any agent was instantiated, preventing both data leakage and wasteful LLM inference tokens.

---

## 3. Test Execution 2: CMS Claim Dossier Read (`GET /claims/CLM-2026-0101`)

### User 1 (Authorized: Jane)

#### User 1 Request:
```http
GET /claims/CLM-2026-0101 HTTP/1.1
Host: api.claimsense.internal
Authorization: Bearer token-jane-full-access
```

#### User 1 Response:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "claim_id": "CLM-2026-0101",
  "claimant": {
    "name": "Sarah Chen",
    "policy_id": "POL-10001",
    "contact": "sarah.chen@example.com"
  },
  "status": "new",
  "incident_date": "2026-03-15",
  "incident_time": "14:30",
  "incident_location": "Intersection of Elm St and Oak Ave, Springfield",
  "incident_description": "Claimant was rear-ended at a traffic light by another vehicle. Minor impact at low speed. Police report filed. No injuries.",
  "vehicle": {
    "make": "Toyota",
    "model": "Camry",
    "year": 2023,
    "vin": "4T1BF1FK5CU000101",
    "market_value": 28000.0
  },
  "damage_description": "Rear bumper cracked, tail light housing broken, minor dent to trunk lid.",
  "repair_estimate": 2800.0,
  "prior_claims": [],
  "created_at": "2026-10-23T02:28:31.463535",
  "assigned_adjuster_id": "adjuster-jane"
}
```

---

### User 2 (Unauthorized: Bob)

#### User 2 Request:
```http
GET /claims/CLM-2026-0101 HTTP/1.1
Host: api.claimsense.internal
Authorization: Bearer token-bob-limited-access
```

#### User 2 Response:
```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "detail": "Access denied: User 'adjuster-bob' is not entitled to claim 'CLM-2026-0101'"
}
```

---

## 4. Immutable Audit Trail Evidence

Every call to the API—whether granted or denied—appends an immutable structured record to `logs/audit_trail.jsonl`. Below are the actual log records captured during this test run:

### Audit Record 1: User 1 Granted Adjudication
```json
{
  "audit_id": "AUD-41D52682D8EC",
  "timestamp": "2026-10-23T03:33:25.528498+00:00",
  "actor": "adjuster-jane",
  "user_id": "adjuster-jane",
  "action": "adjudicate_claim",
  "resource": "CLM-2026-0101",
  "outcome": "granted",
  "decision": "approve",
  "details": {
    "decision_detail": "standard_approval",
    "verdict_source": "model_agent",
    "cited_clauses": [
      "CLS-PER-001",
      "CLS-COV-001"
    ],
    "policy_in_force": true,
    "payout_authorized": 2300.0
  }
}
```

### Audit Record 2: User 1 Granted Claim Read
```json
{
  "audit_id": "AUD-14ED8EC40C6C",
  "timestamp": "2026-10-23T03:33:25.535027+00:00",
  "actor": "adjuster-jane",
  "user_id": "adjuster-jane",
  "action": "read_claim",
  "resource": "CLM-2026-0101",
  "outcome": "granted",
  "decision": null,
  "details": {}
}
```

### Audit Record 3: User 2 Denied Adjudication (Pre-Agent Interception)
```json
{
  "audit_id": "AUD-9784E60CAE16",
  "timestamp": "2026-10-23T03:33:25.538247+00:00",
  "actor": "adjuster-bob",
  "user_id": "adjuster-bob",
  "action": "adjudicate_claim",
  "resource": "CLM-2026-0101",
  "outcome": "denied",
  "decision": "deny",
  "details": {
    "reason": "Access denied: User 'adjuster-bob' is not entitled to claim 'CLM-2026-0101'",
    "stage": "pre_agent_access_control"
  }
}
```

### Audit Record 4: User 2 Denied Claim Read
```json
{
  "audit_id": "AUD-29D051CCB0F3",
  "timestamp": "2026-10-23T03:33:25.540953+00:00",
  "actor": "adjuster-bob",
  "user_id": "adjuster-bob",
  "action": "read_claim",
  "resource": "CLM-2026-0101",
  "outcome": "denied",
  "decision": null,
  "details": {
    "reason": "Access denied: User 'adjuster-bob' is not entitled to claim 'CLM-2026-0101'"
  }
}
```

---

## 5. Verification Against Acceptance Criteria & Area D Rubric

| Criterion / Requirement | Specification | Observed Result | Status |
|---|---|---|---|
| **M4 Req 1** | Data access boundary deployed and callable | FastAPI REST boundary deployed with routes for CMS, DocStore, PolicyAdmin, Adjudication, and Audit Trail. | **PASS** |
| **M4 Req 2** | Authorisation enforced on every route; requests without a valid token are refused | Verified across all 6 routes; missing or invalid token yields `401 Unauthorized` with `WWW-Authenticate: Bearer`. | **PASS** |
| **M4 Req 3** | Access control implemented in code and executed before any agent is invoked | `AccessControlEngine.verify_entitlement` runs prior to claim parsing or pipeline invocation. | **PASS** |
| **M4 Req 4** | Two-user access test recorded, with both requests and both responses, on the same claim | Evidenced above on `CLM-2026-0101` for User 1 (`adjuster-jane`) and User 2 (`adjuster-bob`). | **PASS** |
| **M4 Req 5** | An audit record written for every call, granted or denied, carrying user, action, and resource | Verified in `logs/audit_trail.jsonl` carrying `audit_id`, `timestamp`, `actor`, `action`, `resource`, `outcome`. | **PASS** |
| **AC-2** | Refusal on entitlement: request returns no claim data, refusal appears in audit trail | Bob received HTTP 403 Forbidden with zero claim data leaked; denial recorded in audit log. | **PASS** |
| **Area D Rubric** | Strong (80-100%): Authorisation is enforced in code ahead of any agent, holds on every route, and every call is recorded with user, action and resource, including refusals | Both automated pytest (`test_two_user_access.py`) and script (`run_two_user_test.py`) verify this comprehensively. | **PASS** |

---

## 6. How to Reproduce This Evidence

Anyone can independently reproduce and verify this two-user test using the automated script:

```bash
# 1. Run the automated Pytest suite:
PYTHONPATH=. pytest tests/test_two_user_access.py -v

# 2. Run the demonstration CLI runner:
python3 scripts/run_two_user_test.py

# 3. Query the live audit trail:
curl -H "Authorization: Bearer token-admin-access" http://localhost:8000/audit-trail?limit=10
```
