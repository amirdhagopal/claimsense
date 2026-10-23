# ClaimSense AI — Client System Typed Contracts & Idempotency Rules

**Document Version:** 1.0 (Milestone 2 Deliverable)  
**Implementation Package:** [`src/contracts/`](file:///Users/amirdhagopal/Projects/ik/claimsense/src/contracts)  

---

## 1. Architectural Role of Client Contracts

ClaimSense AI sits between three external enterprise client systems:
1. **Claims Management System (CMS):** System of record for claim lifecycles and confirmed decisions.
2. **Document Store (DocStore):** Repository for supporting physical evidence and notes.
3. **Policy Administration (PolicyAdmin):** Source of truth for coverage grants, exclusions, and clause text.

To ensure deterministic reliability, zero hallucination of data structures, and contract-driven verification, all communication across the client perimeter is governed by strict Pydantic v2 schemas.

---

## 2. Claims Management System (CMS) Contract

### 2.1 Read Operations: `GET /claims/{claim_id}`

Returns the authoritative claim header, claimant info, vehicle specifics, and loss facts:

```json
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
  "incident_description": "Claimant was rear-ended at a traffic light by another vehicle.",
  "vehicle": {
    "make": "Toyota",
    "model": "Camry",
    "year": 2023,
    "vin": "4T1BF1FK5CU000101",
    "market_value": 28000.0
  },
  "damage_description": "Rear bumper cracked, tail light housing broken.",
  "repair_estimate": 2800.0,
  "prior_claims": [],
  "created_at": "2026-03-15T15:00:00Z",
  "assigned_adjuster_id": "adjuster-jane"
}
```

### 2.2 History Operations: `GET /claims/{claim_id}/history`

Returns state machine transitions, actor audits, and previous review timestamps:

```json
{
  "claim_id": "CLM-2026-0101",
  "events": [
    {
      "timestamp": "2026-03-15T15:00:00Z",
      "previous_status": null,
      "new_status": "new",
      "actor_id": "system_fnol",
      "reason": "First notice of loss submitted"
    }
  ]
}
```

### 2.3 Write Operations: `POST /claims/{claim_id}/decisions`

This is the **sole write operation** across all three client systems. It records the final, adjuster-confirmed decision back to CMS.

```json
{
  "idempotency_key": "e4b2d56a-789a-4c12-98ef-123456789abc",
  "claim_id": "CLM-2026-0101",
  "decision": "approve",
  "decision_detail": "standard_approval",
  "adjuster_id": "adjuster-jane",
  "reasoning": "Claimant was rear-ended at red light. Policy active and comprehensive coverage applies under CLS-COV-001. Repair estimate $2,800 is within policy limits.",
  "cited_clauses": ["CLS-PER-001", "CLS-COV-001", "CLS-DED-001"],
  "override_reason": null,
  "payout_authorized": 2300.0
}
```

---

## 3. Idempotency Specification for CMS Write-Backs

Network timeouts, browser double-clicks, or automated retries in distributed systems can easily trigger duplicate write attempts. Because a decision confirmation updates claim status and authorizes payout reserves, **strict idempotency is mandatory**.

### 3.1 Idempotency Rules

1. **Mandatory Unique Key:** Every write request to `POST /claims/{claim_id}/decisions` MUST supply an `idempotency_key` (UUIDv4) in the JSON payload or the HTTP `Idempotency-Key` header.
2. **Payload Fingerprinting:** The server calculates a SHA-256 hash of the normalized request payload:
   $$\text{Fingerprint} = \text{SHA-256}(\text{CanonicalJSON}(\text{Payload}))$$
3. **Idempotency Store (24-Hour TTL):** The CMS maintains an in-memory/Redis cache with 24-hour expiration mapping `idempotency_key -> {fingerprint, response_status, response_body, created_at}`.
4. **Execution Semantics:**
   - **Case A: First Receipt:** Key does not exist in store. Process decision, write to database, store result in cache, return HTTP 201 Created.
   - **Case B: Exact Replay (Safe Idempotent Hit):** Key exists and payload fingerprint matches stored fingerprint. Do NOT re-execute business logic or update database. Return stored response with HTTP 200 OK and header `X-Idempotent-Replay: true` (or payload field `idempotent_replay: true`).
   - **Case C: Conflicting Replay (Payload Mismatch):** Key exists but payload fingerprint differs (e.g. attempting to change decision from `approve` to `deny` using the same idempotency key). Return HTTP 409 Conflict with error code `IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD`.
   - **Case D: Concurrent Requests:** If a second request arrives while the first is in progress, the second request receives HTTP 425 Too Early or waits for lock release.
5. **State Transition Guard:** A claim already in `adjudicated` or `closed` status cannot receive another decision without explicit supervisor re-opening. Attempting to write to an already finalized claim returns HTTP 422 Unprocessable Entity.

---

## 4. Document Store (DocStore) Contract

### 4.1 Read Metadata: `GET /documents?claim_id={claim_id}`

Lists all supporting documents attached to the claim dossier:

```json
{
  "claim_id": "CLM-2026-0101",
  "total_count": 2,
  "documents": [
    {
      "doc_id": "DOC-001-A",
      "claim_id": "CLM-2026-0101",
      "document_type": "police_report",
      "file_name": "police_report_20260315.pdf",
      "file_size_bytes": 245120,
      "mime_type": "application/pdf",
      "sha256_hash": "a1b2c3d4e5f6...",
      "uploaded_at": "2026-03-15T16:00:00Z",
      "flags": []
    }
  ]
}
```

### 4.2 Read Content: `GET /documents/{doc_id}/content`

Retrieves parsed text content and structured annotations for model ingestion:

```json
{
  "doc_id": "DOC-001-A",
  "claim_id": "CLM-2026-0101",
  "document_type": "police_report",
  "content_summary": "Springfield PD report #2026-03-1501. Confirms rear-end collision at intersection. Other driver cited for following too closely. No injuries reported.",
  "structured_data": {
    "police_department": "Springfield PD",
    "report_number": "2026-03-1501",
    "other_driver_cited": true,
    "injuries_reported": false
  },
  "is_redacted": false,
  "retrieved_at": "2026-10-02T10:00:00Z"
}
```

---

## 5. Policy Administration (PolicyAdmin) Contract

### 5.1 Read Policy: `GET /policies/{policy_id}`

Retrieves policyholder coverage terms, vehicle schedule, and limits:

```json
{
  "policy": {
    "policy_id": "POL-10001",
    "policyholder": "Sarah Chen",
    "effective_date": "2026-01-01",
    "expiry_date": "2027-01-01",
    "status": "Active",
    "coverage_type": "Comprehensive",
    "vehicle_schedule": ["4T1BF1FK5CU000101"],
    "clauses": [
      {
        "clause_id": "CLS-PER-001",
        "title": "Policy Period",
        "section": "Period",
        "text": "This policy is in force from the effective date to the expiry date shown on the schedule, both dates inclusive.",
        "applies_to_coverage": ["Comprehensive", "Third-Party Only"]
      }
    ],
    "deductible": 500.0,
    "coverage_limit": 50000.0
  }
}
```

### 5.2 Read Clauses: `GET /policies/{policy_id}/clauses`

Returns the searchable policy clause corpus for retrieval grounding and citation attribution:

```json
{
  "policy_id": "POL-10001",
  "total_clauses": 3,
  "clauses": [
    {
      "clause_id": "CLS-PER-001",
      "title": "Policy Period",
      "section": "Period",
      "text": "This policy is in force from the effective date to the expiry date shown on the schedule, both dates inclusive.",
      "applies_to_coverage": ["Comprehensive"]
    },
    {
      "clause_id": "CLS-COV-001",
      "title": "Comprehensive Coverage",
      "section": "Coverage",
      "text": "We will pay for loss of or damage to the insured vehicle caused by collision, including rear-end collisions, subject to the deductible and coverage limit.",
      "applies_to_coverage": ["Comprehensive"]
    },
    {
      "clause_id": "CLS-DED-001",
      "title": "Standard Deductible",
      "section": "Deductible",
      "text": "A deductible of $500 applies to each claim under this section.",
      "applies_to_coverage": ["Comprehensive"]
    }
  ]
}
```

---

## 6. Contract Verification and Unit Testing

The contracts are validated using automated unit tests in [`tests/test_contracts.py`](file:///Users/amirdhagopal/Projects/ik/claimsense/tests/test_contracts.py), verifying:
- Schema validation and strict field constraints (`extra="forbid"` prevents unknown attributes).
- Clause ID pattern validation (`^CLS-[A-Z]{3}-[0-9]{3}$`).
- Date logic (`is_in_force_on`) and vehicle schedule matching (`covers_vehicle`).
- Idempotency key replay semantics and collision detection.
