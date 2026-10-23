# ClaimSense AI — Synthetic Data Shapes & Canonical Fixtures

**Document Version:** 1.0 (Milestone 2 Deliverable)  
**Implementation Source:** [`src/models/synthetic_shapes.py`](file:///Users/amirdhagopal/Projects/ik/claimsense/src/models/synthetic_shapes.py)  
**Canonical Dataset:** [`data/fixtures/synthetic_dossiers.json`](file:///Users/amirdhagopal/Projects/ik/claimsense/data/fixtures/synthetic_dossiers.json)  

---

## 1. Synthetic Data Mandate and Ethical Boundary

In accordance with Section 3 of the Capstone Brief:
> **Constraint 3: Synthetic data only. No production or personally identifiable data is introduced at any stage.**

All motor claims, policy records, claimant profiles, VINs, addresses, repair estimates, and doctor notes utilized in ClaimSense AI are 100% synthetically generated. Under no circumstances is real policyholder data loaded into memory, storage, or external LLM APIs.

---

## 2. Canonical Motor Policy Clause Taxonomy

To ensure verifiable source attribution (Grading Area C & D), every clause in the synthetic policy corpus adheres to an immutable hierarchical naming standard:

$$\text{Clause Pattern: } \mathbf{\text{CLS-}[A\text{-}Z]\{3\}\text{-}[0\text{-}9]\{3\}}$$

| Section Code | Domain Description | Example Clause IDs |
|---|---|---|
| `CLS-PER-` | **Policy Period, Inception & Territory:** Defines effective dates, geographic bounds, and loss date precedence. | `CLS-PER-001`, `CLS-PER-006` |
| `CLS-COV-` | **Coverage Grants & Perils:** Accidental collision, weather/hail, glass, theft, agreed-value classic, and routing triggers. | `CLS-COV-001` through `CLS-COV-011` |
| `CLS-EXC-` | **Statutory & Policy Exclusions:** Intoxication/DUI, closed-circuit motorsport/racing, unlisted drivers, intentional damage. | `CLS-EXC-001`, `CLS-EXC-003` |
| `CLS-DED-` | **Deductibles & Retentions:** Standard collision deductible ($500), reduced glass waiver ($100), classic vehicle deductible ($1,000). | `CLS-DED-001`, `CLS-DED-002` |
| `CLS-CLM-` | **Claims Conditions & Duties:** Notice of loss timeline, mitigation duties, anti-fraud cooperation. | `CLS-CLM-001` through `CLS-CLM-005` |

### Authoritative Canonical Clauses in `src/models/synthetic_shapes.py`

1. **`CLS-PER-001` (Policy Period):** "This policy is in force from the effective date to the expiry date shown on the schedule, both dates inclusive. No coverage applies outside this period regardless of system status flags."
2. **`CLS-PER-006` (Incident Date Precedence):** "The determining factor for coverage validity is the date on which the loss incident occurred. Losses occurring even one calendar day after policy expiration or cancellation are strictly excluded."
3. **`CLS-COV-001` (Collision Coverage):** "We will pay for loss of or damage to the insured vehicle caused by accidental collision with another vehicle, stationary object, or overturn, subject to applicable deductibles and policy limits."
4. **`CLS-COV-002` (Natural Perils & Hail):** "We will indemnify the policyholder for direct physical loss caused by hail, lightning, storm, windstorm, flood, or falling objects."
5. **`CLS-COV-003` (Automotive Glass):** "Covers repair or replacement of windshield and window glass damaged by road debris or accidental breakage. Subject to a reduced glass deductible of $100."
6. **`CLS-COV-004` (Theft):** "Covers total loss or repair resulting from theft of the insured vehicle."
7. **`CLS-COV-006` (Total Loss Constructive Threshold):** "A vehicle is deemed an economic total loss when the estimated cost of repairs exceeds 75% of the vehicle market value at the time of loss."
8. **`CLS-COV-007` (Bodily Injury Routing):** "Any claim involving hospitalisation, severe soft-tissue trauma, fractures, or third-party injury claims exceeding $5,000 must be routed to a designated Bodily Injury specialist adjuster."
9. **`CLS-COV-008` (Scheduled Vehicle Warranty):** "Coverage applies strictly and exclusively to the vehicle(s) whose Vehicle Identification Number (VIN) is listed on the policy vehicle schedule."
10. **`CLS-COV-009` (Mid-Term Endorsement Verification):** "Coverage upgrades or addition of comprehensive perils initiated via mid-term endorsement are subject to strict fraud verification if a high-severity claim occurs within 72 hours of upgrade."
11. **`CLS-COV-010` & `CLS-COV-011` (Classic Vehicle Agreed Value & Specialist Routing):** Valuation and restoration routing for antique/classic vehicles.
12. **`CLS-EXC-001` (Intoxication Exclusion):** "No coverage applies if the operator of the insured vehicle is convicted of or breathalysed above the statutory Blood Alcohol Concentration (BAC) threshold at the time of loss."
13. **`CLS-EXC-003` (Racing Exclusion):** "No coverage applies to loss, damage, or liability incurred while participating in any organized racing, speed trials, pace-making, or open-track circuit events."
14. **`CLS-DED-001` & `CLS-DED-002` (Deductible Schedules):** $500 collision / $100 glass.

---

## 3. Synthetic Claim Dossier Schema (`SyntheticClaimDossier`)

The consolidated fixture structure bundles all facts needed to evaluate an adjudication pass:

```json
{
  "claim": {
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
    "incident_description": "Claimant was rear-ended at a traffic light by another vehicle...",
    "vehicle": {
      "make": "Toyota",
      "model": "Camry",
      "year": 2023,
      "vin": "4T1BF1FK5CU000101",
      "market_value": 28000.0
    },
    "damage_description": "Rear bumper cracked, tail light housing broken...",
    "repair_estimate": 2800.0,
    "prior_claims": []
  },
  "policy": {
    "policy_id": "POL-10001",
    "policyholder": "Sarah Chen",
    "effective_date": "2026-01-01",
    "expiry_date": "2027-01-01",
    "status": "Active",
    "coverage_type": "Comprehensive",
    "vehicle_schedule": ["4T1BF1FK5CU000101"],
    "clauses": [...],
    "deductible": 500.0,
    "coverage_limit": 50000.0
  },
  "documents": [
    {
      "doc_id": "DOC-001-A",
      "claim_id": "CLM-2026-0101",
      "document_type": "police_report",
      "content_summary": "Springfield PD report #2026-03-1501...",
      "structured_data": {},
      "is_redacted": false
    }
  ],
  "ground_truth_decision": "approve",
  "ground_truth_fraud": false,
  "ground_truth_detail": null,
  "expected_citations": ["CLS-PER-001", "CLS-COV-001", "CLS-DED-001"]
}
```

---

## 4. Fixture Generation and Schema Verification

To regenerate or validate fixtures:

```bash
PYTHONPATH=. python3 scripts/generate_fixtures.py
```

This validates all 20 canonical cases against the Pydantic v2 schemas and writes the compiled output to [`data/fixtures/synthetic_dossiers.json`](file:///Users/amirdhagopal/Projects/ik/claimsense/data/fixtures/synthetic_dossiers.json).
