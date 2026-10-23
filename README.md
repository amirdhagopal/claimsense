# ClaimSense AI

A claims adjudication co-pilot that compresses first-pass claim decisions from hours to minutes — with reasoning recorded, evidence cited, and a licensed adjuster accountable for every outcome.

**Engagement:** Five-week FDE capstone · AWS + OpenAI Agents SDK  
**Repository:** https://github.com/amirdhagopal/claimsense  
**Data:** 100% synthetic — no production or personally identifiable data at any stage.

---

## Architecture Overview

```
  Claim → Documents → Policy → History
              │
  ┌───────────▼────────────────────────────────────┐
  │           Deterministic Spine                    │
  │  identity · access control · policy dates · money │
  │  Runs BEFORE any agent. Rejects if unauthorized.  │
  ├────────────────────────────────────────────────────┤
  │           Agent Pipeline (OpenAI Agents SDK)       │
  │  1. File Reader → 2. Coverage → 3. Risk → 4. Draft│
  │  Every judgment cites the evidence it relied on.   │
  └──────────────────────┬─────────────────────────────┘
                         │
                         ▼
                 First Decision
             reasoning + citations
                         │
                         ▼
               Licensed Adjuster
            confirms every outcome
```

### The Four Decision Outcomes

| Decision | When |
|----------|------|
| **Approve** | Policy in force, coverage applies, no risk indicators |
| **Flag / Refer** | Fraud indicators, narrative contradictions, suspicious patterns |
| **Route** | Total loss, bodily injury, or specialist assessment required |
| **Deny** | Policy lapsed, excluded peril, vehicle not scheduled |

---

## Repository Structure

```
claimsense/
├── docs/
│   ├── charter.md                  # Engagement charter (M1)
│   ├── raci.md                     # Stakeholder map & RACI (M1)
│   ├── success-criteria.md         # Four quantified success criteria (M1)
│   ├── sow.md                      # Statement of Work (2 pages) (M2)
│   ├── architecture.md             # System architecture & boundary specification (M2)
│   ├── pricing.md                  # Commercial pricing & unit economics model (M2)
│   ├── risk-register.md            # Risk register (6 risks) & mitigations (M2)
│   ├── contracts.md                # Typed client system contracts & idempotency rules (M2)
│   ├── synthetic-data-shapes.md    # Synthetic data shapes & clause taxonomy (M2)
│   ├── cloud-provisioning.md       # AWS account provisioning evidence & manifest (M2)
│   ├── milestone3_deliverables.md  # Milestone 3 production agents & CI gate report (M3)
│   ├── two-user-access-test.md     # Two-user access test evidence on CLM-2026-0101 (M4)
│   ├── milestone4_deliverables.md  # Milestone 4 trust boundary & audit trail report (M4)
│   ├── runbook.md                  # Operational runbook (4 required procedures) (M5)
│   ├── incident-report.md          # Post-incident drill report (SEV-2 latency recovery) (M5)
│   ├── observation-document.md     # Capstone observation document (6 sections) (M5)
│   ├── presentation.md             # Client executive presentation & demo script (M5)
│   └── handover-pack.md            # Consolidated engagement handover pack (M5)
├── src/
│   ├── agents/                     # OpenAI Agents SDK 4-Agent Pipeline (M3)
│   │   ├── base.py                 # BaseAgent with typed parsing & fallback
│   │   ├── file_reader.py          # Agent 1: FileReaderAgent
│   │   ├── coverage.py             # Agent 2: CoverageAgent (RAG + citations)
│   │   ├── risk_assessment.py      # Agent 3: RiskAssessmentAgent (fraud/total loss/BI)
│   │   ├── decision_drafter.py     # Agent 4: DecisionDraftAgent (4 outcomes)
│   │   ├── pipeline.py             # Adjudication pipeline orchestrator
│   │   └── schemas.py              # Strict Pydantic I/O models
│   ├── spine/                      # Deterministic code spine (M3/M4/M5)
│   │   ├── access_control.py       # Pre-agent entitlement checks (M3/M4)
│   │   ├── security.py             # Route-level Bearer auth & HMAC signing (M4)
│   │   ├── metrics.py              # Operational telemetry & CloudWatch alarms (M5)
│   │   ├── date_engine.py          # Policy effective date verification (M3)
│   │   ├── financial_engine.py     # Deductibles & monetary calculations (M3)
│   │   ├── audit_logger.py         # Append-only immutable audit trail (M3/M4)
│   │   ├── context.py              # SpineContext struct
│   │   └── orchestrator.py         # Pre-agent invariant coordinator
│   ├── retrieval/                  # Policy clause retrieval engine (M3)
│   │   └── policy_index.py         # Searchable BM25 corpus & citation grounding
│   ├── api/                        # FastAPI REST Service & Interactive Web UI (M3/M4/M5)
│   │   ├── app.py                  # Guarded routes: /health, /adjudicate, /claims, /dashboard, /audit-trail
│   │   └── static/index.html       # Glassmorphic Adjuster Co-Pilot Web Application (M5)
│   ├── contracts/                  # Pydantic v2 client contracts (M2)
│   └── models/                     # Canonical synthetic data shapes (M2)
├── infra/                          # Terraform Infrastructure as Code (M2)
├── data/fixtures/                  # 20 validated synthetic claim dossiers
├── evals/
│   ├── run_pipeline_evals.py       # CI evaluation gate runner (M3/M5)
│   ├── run_evals.py                # Schema & distribution validator (M1/M5)
│   ├── schema.json                 # JSON schema definition
│   └── cases/
│       ├── milestone1_cases.json   # Initial 20 cases (EVAL-001 to EVAL-020)
│       └── milestone5_cases.json   # Milestone 5 cases (EVAL-021 to EVAL-150)
├── scripts/
│   ├── run_two_user_test.py        # CLI demonstration runner for Two-User Access Test (M4)
│   └── generate_150_cases.py       # Evaluation suite synthetic generator (M5)
├── tests/                          # Automated Pytest suite (37 passing tests)
├── .github/workflows/ci.yml        # CI pipeline blocking image push on eval gate (M3)
├── Dockerfile                      # Production multi-stage Dockerfile (M3)
├── docker-compose.yml              # Single-command local orchestration (M3)
├── requirements.txt                # Pinned dependencies
├── DECISIONS.md                    # Architectural decision records (ADRs 001–014)
└── README.md                       # This file
```

---

## Milestone Progress

- [x] **M1 — Discovery & Scoping** (Week 1)
  - [x] Engagement charter (`docs/charter.md`)
  - [x] Stakeholder map & RACI (`docs/raci.md`)
  - [x] Four quantified success criteria (`docs/success-criteria.md`)
  - [x] DECISIONS.md with 5 dated ADRs (ADR-001–005)
  - [x] 20 evaluation cases including adversarial families (`evals/cases/`)
- [x] **M2 — Design, Pricing & Architecture** (Week 2)
  - [x] Statement of Work (2-page contract) (`docs/sow.md`)
  - [x] Labeled architecture diagram & boundary justification (`docs/architecture.md`)
  - [x] Pricing model with assumptions stated (`docs/pricing.md`)
  - [x] Risk register of 6 risks anticipating later failures (`docs/risk-register.md`)
  - [x] Typed client contracts with idempotency rules (`src/contracts/`, `docs/contracts.md`)
  - [x] Synthetic data shapes & canonical fixtures (`src/models/`, `data/fixtures/`)
  - [x] Cloud provisioning evidence & Terraform IaC (`infra/`, `docs/cloud-provisioning.md`)
  - [x] ADR-006, ADR-007, and ADR-008 in `DECISIONS.md`
- [x] **M3 — Production Agents & CI Gate** (Week 3)
  - [x] 4-Agent adjudication set on OpenAI Agents SDK (`src/agents/`) with strict Pydantic schemas
  - [x] Searchable policy clause corpus with BM25 ranking & citation grounding (`src/retrieval/`)
  - [x] Deterministic spine pre-agent guards & financial engine (`src/spine/`)
  - [x] FastAPI REST service (`/health`, `/adjudicate`, `/claims/{id}/decisions`)
  - [x] Multi-stage Dockerfile & single-command local orchestration (`docker compose up`)
  - [x] GitHub Actions CI pipeline (`.github/workflows/ci.yml`) with automated evaluation gate
  - [x] All 4 decision outcomes correctly produced with explicit model vs fallback attribution
  - [x] ADR-009 and ADR-010 in `DECISIONS.md`
- [x] **M4 — Integration and Access Control (Trust Boundary & Audit Trail)** (Week 4)
  - [x] Data access boundary deployed and callable (`src/api/app.py`)
  - [x] Authorisation enforced on every route; requests without a valid token are refused (`src/spine/security.py`, 401 Unauthorized)
  - [x] Access control implemented in code and executed before any agent is invoked (`src/spine/access_control.py`, 403 Forbidden with zero claim leakage)
  - [x] Two-user access test recorded, with both requests and both responses, on the same claim `CLM-2026-0101` (`docs/two-user-access-test.md`, `scripts/run_two_user_test.py`, `tests/test_two_user_access.py`)
  - [x] An audit record written for every call, granted or denied, carrying user, action and resource (`src/spine/audit_logger.py`, `logs/audit_trail.jsonl`)
  - [x] ADR-011 and ADR-012 in `DECISIONS.md`
- [x] **M5 — Evaluation, Observability, Reliability and Handover** (Week 5)
  - [x] Evaluation suite of 150 cases including adversarial families: prompt injection, cross-record leakage, forced auto-decision (`evals/cases/`)
  - [x] Operational dashboard reporting error rate, call volume, and p95 latency, with CloudWatch alarms defined (`src/spine/metrics.py`, `/dashboard/metrics`)
  - [x] Interactive claims adjuster co-pilot web application (`src/api/static/index.html`, `/dashboard`)
  - [x] Incident drill: deliberate regression, detection, rollback, and 1-page incident report recording MTTR recovery (`docs/incident-report.md`)
  - [x] Operational runbook covering 4 procedures: add user, roll back deployment, escalate flagged claim, update policy corpus (`docs/runbook.md`)
  - [x] Capstone observation document covering 6 required sections (`docs/observation-document.md`)
  - [x] Client executive presentation deck & demo script (`docs/presentation.md`)
  - [x] Consolidated engagement handover pack (`docs/handover-pack.md`)
  - [x] ADR-013 and ADR-014 in `DECISIONS.md`

---

## 150-Case Evaluation Suite Matrix

Validate all 150 evaluation cases:

```bash
python evals/run_evals.py
```

### Full Distribution (150 Cases)

| Decision Outcome | Count | % of Corpus | Target Peril Types & Categories |
|---|---|---|---|
| **Approve** | 49 | 32.7% | Collision, Glass, Weather/Hail, Tree fall, Animal strike, Vandalism |
| **Deny** | 40 | 26.7% | Lapsed policy, Racing/track exclusion, DUI exclusion, Rideshare, VIN mismatch |
| **Flag / Refer** | 32 | 21.3% | Fraud red flags, Staged collisions, Timing anomalies, Contradictions, Injections |
| **Route** | 29 | 19.3% | Constructive total loss (>75% ACV), Bodily injury, Classic vehicle specialist |

**Adversarial Families Breakdown (33 Cases):**
- **Cross-Record Leakage (9 cases):** Adjusters attempting to query claims outside their entitlement. Pre-agent spine refuses in code with HTTP 403 Forbidden.
- **Prompt Injection (8 cases):** Injected instructions in narratives attempting to force auto-approval. System treats input strictly as untrusted evidence.
- **Forced Auto-Decision (8 cases):** Executive override headers attempting to bypass human sign-off.
- **Narrative Contradiction (8 cases):** Airbag burn claims contradicted by vehicle ECM diagnostic data.

---

## Quick Start: Interactive Co-Pilot Web Application

1. **Launch the Local Service:**
   ```bash
   uvicorn src.api.app:app --host 0.0.0.0 --port 8000
   ```
2. **Open the Web Interface:**
   Navigate to [http://localhost:8000/](http://localhost:8000/) or [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
3. **Explore Features:**
   - Run AI Adjudication on any motor claim dossier
   - Test Two-User Trust Boundary refusal (Bob vs Jane on `CLM-2026-0101`)
   - Monitor real-time CloudWatch telemetry (Call volume, error rate, p95 latency)
   - Trigger the Incident Recovery Drill and verify automated SLA restoration

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.12+ |
| Agent Framework | OpenAI Agents SDK |
| Retrieval | Searchable policy clause corpus |
| Containers | Docker |
| CI | Evaluation gate (blocks push on failure) |
| Cloud | AWS (ECS, CloudWatch) |

---

## Three Inviolable Constraints

1. **Deterministic operations are implemented in code.** Identity, access control, policy dates, and monetary calculations are never delegated to a model.
2. **Judgment is delegated to a model, and is cited.** Every judgment states the evidence it relied on.
3. **Synthetic data only.** No production or personally identifiable data is introduced at any stage.
