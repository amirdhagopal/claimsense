# ClaimSense AI — Engagement Handover Pack

**Client:** Motor Claims Insurer Engagement  
**Forward Deployed Engineer:** Amirdha Gopal  
**Engagement Schedule:** 5-Week Fixed-Price Engagement ($85,000 Milestone Contract)  
**Handover Date:** 23 October 2026  
**Final Release Tag:** `v1.0.0`  
**GitHub Repository:** https://github.com/amirdhagopal/claimsense  

---

## 1. Master Deliverables Index

| Milestone | Deliverable Name | File Location | Status |
|---|---|---|---|
| **M1** | Project Charter & Scope | [`docs/charter.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/docs/charter.md) | Accepted |
| **M1** | Stakeholder Map & RACI Matrix | [`docs/raci.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/docs/raci.md) | Accepted |
| **M1** | Four Quantified Success Criteria | [`docs/success-criteria.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/docs/success-criteria.md) | Accepted |
| **M1** | Baseline Evaluation Suite (20 cases) | [`evals/cases/milestone1_cases.json`](file:///Users/amirdhagopal/Projects/ik/claimsense/evals/cases/milestone1_cases.json) | Validated |
| **M2** | Commercial Statement of Work (SoW) | [`docs/sow.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/docs/sow.md) | Signed |
| **M2** | Architecture & Boundary Justification | [`docs/architecture.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/docs/architecture.md) | Accepted |
| **M2** | Pricing & Unit Economics Model | [`docs/pricing.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/docs/pricing.md) | Accepted |
| **M2** | Risk Register (6 Anticipated Risks) | [`docs/risk-register.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/docs/risk-register.md) | Monitored |
| **M2** | Typed Client Contracts (CMS/Doc/Policy) | [`src/contracts/`](file:///Users/amirdhagopal/Projects/ik/claimsense/src/contracts/) | Verified |
| **M2** | Terraform Cloud Infrastructure | [`infra/`](file:///Users/amirdhagopal/Projects/ik/claimsense/infra/) | Validated |
| **M3** | 4-Agent Pipeline (OpenAI Agents SDK) | [`src/agents/`](file:///Users/amirdhagopal/Projects/ik/claimsense/src/agents/) | Deployed |
| **M3** | BM25 Grounded Policy Clause Index | [`src/retrieval/`](file:///Users/amirdhagopal/Projects/ik/claimsense/src/retrieval/) | Grounded |
| **M3** | Deterministic Pre-Agent Spine | [`src/spine/`](file:///Users/amirdhagopal/Projects/ik/claimsense/src/spine/) | Enforced |
| **M3** | CI Pipeline with Evaluation Gate | [`.github/workflows/ci.yml`](file:///Users/amirdhagopal/Projects/ik/claimsense/.github/workflows/ci.yml) | Active |
| **M4** | Route-Level Bearer Token Security | [`src/spine/security.py`](file:///Users/amirdhagopal/Projects/ik/claimsense/src/spine/security.py) | Verified |
| **M4** | Two-User Access Control Test Evidence | [`docs/two-user-access-test.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/docs/two-user-access-test.md) | Certified |
| **M5** | 150-Case Comprehensive Evaluation Suite | [`evals/cases/`](file:///Users/amirdhagopal/Projects/ik/claimsense/evals/cases/) | Passed (150/150) |
| **M5** | Real-Time Telemetry & SLA Alarms | [`src/spine/metrics.py`](file:///Users/amirdhagopal/Projects/ik/claimsense/src/spine/metrics.py) | Monitored |
| **M5** | Interactive Adjuster Co-Pilot Web UI | [`src/api/static/index.html`](file:///Users/amirdhagopal/Projects/ik/claimsense/src/api/static/index.html) | Live |
| **M5** | Post-Incident Recovery Drill Report | [`docs/incident-report.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/docs/incident-report.md) | Recovered (2m 45s) |
| **M5** | Operational Runbook (4 Procedures) | [`docs/runbook.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/docs/runbook.md) | Handed Over |
| **M5** | Observation Document (6 Sections) | [`docs/observation-document.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/docs/observation-document.md) | Completed |
| **M5** | Client Presentation & Script | [`docs/presentation.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/docs/presentation.md) | Delivered |
| **All** | Architectural Decision Records (14 ADRs)| [`DECISIONS.md`](file:///Users/amirdhagopal/Projects/ik/claimsense/DECISIONS.md) | Documented |

---

## 2. Key Operational Endpoints

- **Interactive Co-Pilot & Dashboard:** `http://localhost:8000/` or `http://localhost:8000/dashboard`
- **Telemetry Metrics JSON:** `http://localhost:8000/dashboard/metrics`
- **Service Health Check:** `http://localhost:8000/health`
- **Adjudication Endpoint:** `POST http://localhost:8000/adjudicate` (Requires `Authorization: Bearer <token>`)
- **Immutable Audit Trail:** `GET http://localhost:8000/audit-trail` (Requires `Authorization: Bearer <token>`)
- **Decision Confirmation Write-Back:** `POST http://localhost:8000/claims/{claim_id}/decisions`

---

## 3. Operational Contacts & Ownership Transfer

- **Primary Handover Lead:** Amirdha Gopal (Forward Deployed Engineer)
- **Client Lead Adjuster:** Adjuster Lead (Operations Transition)
- **Client Platform Lead:** Head of Cloud & Platform Engineering
- **Support Window:** 30-Day Hypercare Warranty Period ending 22 November 2026.
