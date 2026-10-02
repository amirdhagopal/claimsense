# ClaimSense AI — Engagement Charter

**Client:** Apex Motor Insurance Ltd (synthetic entity)
**Engagement Lead (FDE):** Amirdha Gopal
**Duration:** Five weeks (Weeks 12–16)
**Document version:** 1.0 — 1 October 2026

---

## 1. Background

Apex Motor Insurance processes ~4,200 motor claims per month through a team of 38 licensed adjusters. Each adjuster manually navigates three disconnected systems to gather a claim file, verify policy coverage, assess risk (fraud, total-loss, bodily-injury), and write a first decision. Average time-to-first-decision is 47 minutes; variance between adjusters is high and reasoning is never recorded.

Management has identified three bottlenecks:

| # | Bottleneck | Impact |
|---|-----------|--------|
| 1 | **File assembly is manual** — the three systems share no integration; the adjuster is the integration layer. | ~18 min per claim spent re-keying and cross-checking. |
| 2 | **Judgment is invisible** — two adjusters reach different decisions on the same file with no audit trail of why. | Regulatory risk; inconsistent customer outcomes. |
| 3 | **Risk detection is a threshold** — fraud referral fires on a score, not on a reading of the file. Contradictory narratives and suspicious timing patterns are invisible. | Fraud leakage estimated at 3–5% of indemnity spend. |

Extending the existing rule table does not address bottlenecks 2 and 3 because coverage depends on reading policy clause wording and fraud assessment depends on narrative consistency across documents.

## 2. The Three Client Systems

### 2.1 Claims Management System (CMS)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | System of record for all open and closed claims. |
| **Key data** | Claim ID, claimant details, incident description, incident date/time/location, vehicle information, damage description, repair estimate, claim status, adjuster assignment. |
| **Integration point** | REST API — `GET /claims/{claim_id}` returns the full claim record. `GET /claims/{claim_id}/history` returns status transitions. Write-back of the adjuster-confirmed decision via `POST /claims/{claim_id}/decisions` (idempotent on `decision_id`). |
| **Latency** | p95 < 200 ms for reads. |

### 2.2 Document Store (DocStore)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Stores all supporting documents attached to a claim: police reports, medical reports, repair estimates, photos, witness statements, correspondence. |
| **Key data** | Document ID, claim ID (foreign key), document type, upload timestamp, file content (PDF/image). |
| **Integration point** | REST API — `GET /documents?claim_id={claim_id}` returns metadata and signed URLs. `GET /documents/{doc_id}/content` returns the document body. Read-only from ClaimSense's perspective. |
| **Latency** | p95 < 500 ms for document content retrieval. |

### 2.3 Policy Administration System (PolicyAdmin)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Master record for all active and expired policies, including endorsements, exclusions, and clause text. |
| **Key data** | Policy ID, policyholder, vehicle schedule, coverage sections, clause identifiers (e.g., `CLS-PER-006`), effective dates, premium, status. |
| **Integration point** | REST API — `GET /policies/{policy_id}` returns the policy with all clauses. `GET /policies/{policy_id}/clauses` returns individual clause text for retrieval indexing. Read-only from ClaimSense's perspective. |
| **Latency** | p95 < 300 ms. |

### 2.4 Integration Architecture (Milestone 1 view)

```
┌───────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Claims Mgmt  │     │   Document Store  │     │  Policy Admin    │
│    (CMS)      │     │    (DocStore)     │     │  (PolicyAdmin)   │
└──────┬────────┘     └──────┬───────────┘     └──────┬───────────┘
       │ REST                │ REST                    │ REST
       ▼                     ▼                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ClaimSense AI Service                      │
│  ┌─────────────────────┐   ┌──────────────────────────────────┐ │
│  │  Deterministic Spine │   │  Agent Pipeline (OpenAI SDK)    │ │
│  │  • Identity & Auth   │──▶│  • File Reader Agent            │ │
│  │  • Policy Dates      │   │  • Coverage Agent               │ │
│  │  • Money / Arithmetic│   │  • Risk Assessment Agent        │ │
│  │  • Access Control    │   │  • Decision Draft Agent         │ │
│  └─────────────────────┘   └──────────────────────────────────┘ │
│                                      │                          │
│                          ┌───────────▼──────────┐               │
│                          │  First Decision +    │               │
│                          │  Reasoning + Citations│              │
│                          └───────────┬──────────┘               │
└──────────────────────────────────────┼──────────────────────────┘
                                       │
                                       ▼
                              Licensed Adjuster
                              confirms every outcome
```

## 3. Engagement Scope

### In scope

- Claims adjudication co-pilot covering all four decision outcomes: **Approve**, **Flag/Refer**, **Route** (total-loss / bodily-injury / specialist), **Deny**.
- Deterministic spine handling identity, access control, policy date verification, and monetary arithmetic — executed before any agent runs.
- Agent pipeline on the OpenAI Agents SDK with strict typed outputs, every judgment citing the evidence it relied on.
- Retrieval over a searchable motor policy corpus with clause-level citation (e.g., `CLS-PER-006`).
- Synthetic data only — 100% synthetic claims, policies, and supporting documents.
- Trust boundary: service-level authentication, route-level authorisation, immutable audit trail.
- Containerised deployment on AWS with CI evaluation gate.

### Out of scope

- Integration with real/production client systems.
- Automated payout or settlement processing.
- Direct communication with claimants.
- Modification of existing CMS, DocStore, or PolicyAdmin systems.
- Training or fine-tuning of foundation models.

## 4. Engagement Timeline

| Week | Milestone | Key deliverable |
|------|-----------|-----------------|
| 1 | Discovery & Scoping | Charter, RACI, success criteria, DECISIONS.md, 20 eval cases |
| 2 | Design & SoW | SoW, architecture diagram, pricing, risk register, contracts |
| 3 | Build Agents | Agents on OpenAI SDK, RAG, containers, CI eval gate |
| 4 | Integrate & Guard | Auth on every route, access control before agents, audit trail |
| 5 | Handover | 150 eval cases, dashboard, incident drill, runbook, demo |

## 5. Assumptions and Dependencies

| # | Assumption | Risk if invalid |
|---|-----------|-----------------|
| 1 | All three client system APIs are available as synthetic stubs within ClaimSense. | Integration blocked; mitigated by building stubs in Week 1. |
| 2 | OpenAI API access is available with sufficient quota for development and evaluation. | Agent development blocked; mitigated by early key provisioning. |
| 3 | AWS account is provisioned with permissions for ECS/ECR, CloudWatch, and IAM. | Deployment blocked; mitigated by account setup in Week 1. |
| 4 | Policy corpus contains clause-level identifiers that are stable across versions. | Citation grounding impossible; mitigated by designing identifiers in synthetic data. |

## 6. Approval

| Role | Name | Date |
|------|------|------|
| Engagement Lead (FDE) | Amirdha Gopal | 1 Oct 2026 |
| Client Sponsor | [Synthetic — Apex Motor Insurance] | — |
