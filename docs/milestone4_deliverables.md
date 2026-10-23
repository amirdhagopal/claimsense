# ClaimSense AI — Milestone 4 Deliverables: Integration and Access Control

**Status:** 100% COMPLETE & VERIFIED  
**Date:** 23 October 2026  
**Engagement:** Forward Deployed Engineer (FDE) Capstone — Week 4  
**Assessed Area:** Area D (The Trust Boundary — 20% Course Weight)  
**Target Standard:** Strong (80%–100%)

---

## Executive Summary

Milestone 4 establishes the deterministic trust perimeter and immutable audit trail for ClaimSense AI. In strict compliance with the project charter, commercial Statement of Work, and course grading criteria, all access control policies are executed in deterministic Python code at the HTTP boundary **before** any AI agent or LLM interface is invoked.

No model prompt is ever relied upon to enforce security, identity, or claim entitlements, completely eliminating the possibility of prompt injection bypasses or accidental data leakage.

---

## 1. Milestone 4 Checklist & Evidence Directory

| Milestone Deliverable | Implementation Artifact | Verification Evidence | Status |
|---|---|---|---|
| **1. Data access boundary deployed and callable** | [`src/api/app.py`](file:///Users/amirdhagopal/Projects/ik/claimsense/src/api/app.py) | REST API exposing `/adjudicate`, `/claims/{id}`, `/documents`, `/policies/{id}`, `/claims/{id}/decisions`, `/audit-trail`, and `/health`. | **COMPLETE** |
| **2. Authorisation enforced on every route (401 on missing/invalid token)** | [`src/spine/security.py`](file:///Users/amirdhagopal/Projects/ik/claimsense/src/spine/security.py) | `authenticate_request` dependency verifies HMAC-SHA256 tokens. Tested across all 6 routes in `tests/test_api.py`. | **COMPLETE** |
| **3. Access control in code executed before any agent is invoked (403 on lack of entitlement)** | [`src/spine/access_control.py`](file:///Users/amirdhagopal/Projects/ik/claimsense/src/spine/access_control.py) | `AccessControlEngine.verify_entitlement` runs ahead of agent pipeline. Zero claim data returned on 403. | **COMPLETE** |
| **4. Two-user access test recorded with both requests and both responses on same claim** | [`docs/two-user-access-test.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/docs/two-user-access-test.md)<br>[`scripts/run_two_user_test.py`](file:///Users/amirdhagopal/Projects/ik/claimsense/scripts/run_two_user_test.py) | Tested User 1 (`adjuster-jane`) vs. User 2 (`adjuster-bob`) on `CLM-2026-0101`. Automated test in `tests/test_two_user_access.py`. | **COMPLETE** |
| **5. Audit record written for every call, granted or denied, carrying user, action, and resource** | [`src/spine/audit_logger.py`](file:///Users/amirdhagopal/Projects/ik/claimsense/src/spine/audit_logger.py)<br>`logs/audit_trail.jsonl` | Append-only audit logger capturing `audit_id`, `timestamp`, `actor`, `user_id`, `action`, `resource`, `outcome`, `decision`, `details`. | **COMPLETE** |
| **6. Architectural Decision Records** | [`DECISIONS.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/DECISIONS.md) | **ADR-011:** Uniform Bearer token authentication.<br>**ADR-012:** Pre-agent entitlement verification with zero-leakage refusal. | **COMPLETE** |

---

## 2. Trust Boundary Architecture

```mermaid
flowchart TD
    subgraph Client["Untrusted External Adjuster Client"]
        Req1["Request: POST /adjudicate\nClaim: CLM-2026-0101\nAuth: Bearer token"]
    end

    subgraph TrustPerimeter["Deterministic Trust Perimeter (Spine)"]
        AuthCheck{"1. Route-Level Auth\n(TokenManager.verify_token)"}
        EntitleCheck{"2. Pre-Agent Entitlement\n(AccessControlEngine.verify)"}
        AuditLog["3. Immutable Audit Logger\n(logs/audit_trail.jsonl)"]
    end

    subgraph DecisionBoundary["Adjudication & Data Access"]
        Denied401["HTTP 401 Unauthorized\n(Missing or Forged Token)"]
        Denied403["HTTP 403 Forbidden\n(Zero Claim Data Leaked)"]
        Allowed["Deterministic Spine Checks +\n4-Agent Pipeline Execution"]
    end

    Req1 --> AuthCheck
    AuthCheck -- "Invalid / Missing" --> Denied401
    AuthCheck -- "Valid Token" --> EntitleCheck
    EntitleCheck -- "Unauthorized Adjuster" --> Denied403
    EntitleCheck -- "Authorized Adjuster" --> Allowed

    Denied401 -.-> AuditLog
    Denied403 -.-> AuditLog
    Allowed -.-> AuditLog
```

---

## 3. Two-User Access Control Test Results Summary

Target Motor Claim: `CLM-2026-0101` (Claimant: Sarah Chen, Toyota Camry rear bumper impact)

- **User 1 (Jane — Authorized):**
  - Identity: `adjuster-jane`, Role: `licensed_adjuster`, Entitlement: `["*"]`
  - Request: `POST /adjudicate` with `Authorization: Bearer token-jane-full-access`
  - Result: **HTTP 200 OK**
  - Outcome: Adjudication dossier generated, reasoning cited, payout authorized ($2,300), audit log `outcome: "granted"`.
- **User 2 (Bob — Unauthorized):**
  - Identity: `adjuster-bob`, Role: `licensed_adjuster`, Entitlement: `["CLM-2026-0104", "CLM-2026-0109", "CLM-2026-0113"]`
  - Request: `POST /adjudicate` with `Authorization: Bearer token-bob-limited-access`
  - Result: **HTTP 403 Forbidden**
  - Detail: `"Access denied: User 'adjuster-bob' is not entitled to claim 'CLM-2026-0101'"`
  - Zero Leakage: Response contains **zero** claim fields, **zero** vehicle data, **zero** financial numbers.
  - Interception: Evaluated and rejected in deterministic code before any agent was instantiated.
  - Audit Trail: Recorded in `logs/audit_trail.jsonl` with `outcome: "denied"`, `stage: "pre_agent_access_control"`.

---

## 4. Test Execution & Coverage Evidence

The full unit and integration test suite now comprises **37 passing tests**:

```text
$ PYTHONPATH=. pytest tests/ -v
============================= test session starts ==============================
collected 37 items

tests/test_api.py::test_health_endpoint PASSED                           [  2%]
tests/test_api.py::test_all_routes_refuse_unauthenticated_requests[get-/claims/CLM-2026-0101-None] PASSED [  5%]
tests/test_api.py::test_all_routes_refuse_unauthenticated_requests[post-/adjudicate-json_payload1] PASSED [  8%]
tests/test_api.py::test_all_routes_refuse_unauthenticated_requests[get-/documents?claim_id=CLM-2026-0101-None] PASSED [ 10%]
tests/test_api.py::test_all_routes_refuse_unauthenticated_requests[get-/policies/POL-10001-None] PASSED [ 13%]
tests/test_api.py::test_all_routes_refuse_unauthenticated_requests[post-/claims/CLM-2026-0101/decisions-json_payload4] PASSED [ 16%]
tests/test_api.py::test_all_routes_refuse_unauthenticated_requests[get-/audit-trail-None] PASSED [ 18%]
tests/test_api.py::test_malformed_authorization_header PASSED            [ 21%]
tests/test_api.py::test_invalid_bearer_token PASSED                      [ 24%]
tests/test_api.py::test_cryptographic_hmac_token_lifecycle PASSED        [ 27%]
tests/test_api.py::test_get_mock_claim_authorized PASSED                 [ 29%]
tests/test_api.py::test_get_documents_authorized PASSED                  [ 32%]
tests/test_api.py::test_get_policy_authorized PASSED                     [ 35%]
tests/test_api.py::test_adjudicate_unauthorized_refusal_zero_leakage PASSED [ 37%]
tests/test_api.py::test_get_claim_unauthorized_refusal PASSED            [ 40%]
tests/test_api.py::test_get_documents_unauthorized_refusal PASSED        [ 43%]
tests/test_api.py::test_decision_write_unauthorized_refusal PASSED       [ 45%]
tests/test_api.py::test_idempotent_decision_write_back PASSED            [ 48%]
tests/test_api.py::test_audit_trail_endpoint PASSED                      [ 51%]
tests/test_contracts.py::test_claim_record_validation PASSED             [ 54%]
tests/test_contracts.py::test_claim_record_invalid_id PASSED             [ 56%]
tests/test_contracts.py::test_decision_request_idempotency_key_validation PASSED [ 59%]
tests/test_contracts.py::test_policy_deterministic_date_math PASSED      [ 62%]
tests/test_contracts.py::test_clause_citation_regex PASSED               [ 64%]
tests/test_retrieval.py::test_index_initialization PASSED                [ 67%]
tests/test_retrieval.py::test_search_collision PASSED                    [ 70%]
tests/test_retrieval.py::test_search_hail_weather PASSED                 [ 72%]
tests/test_retrieval.py::test_search_exclusions PASSED                   [ 75%]
tests/test_retrieval.py::test_validate_citations PASSED                  [ 78%]
tests/test_spine.py::test_access_control_authorized PASSED               [ 81%]
tests/test_spine.py::test_access_control_unauthorized PASSED             [ 83%]
tests/test_spine.py::test_spine_throws_on_unauthorized PASSED            [ 86%]
tests/test_spine.py::test_date_engine_lapsed_policy PASSED               [ 89%]
tests/test_spine.py::test_financial_engine_calculations PASSED           [ 91%]
tests/test_spine.py::test_financial_engine_total_loss PASSED             [ 94%]
tests/test_spine.py::test_audit_logger_records_to_file PASSED            [ 97%]
tests/test_two_user_access.py::test_two_user_access_on_same_claim PASSED [100%]

============================== 37 passed in 23.80s =============================
```
