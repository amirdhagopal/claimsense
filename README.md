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
│   └── milestone3_deliverables.md  # Milestone 3 production agents & CI gate report (M3)
├── src/
│   ├── agents/                     # OpenAI Agents SDK 4-Agent Pipeline (M3)
│   │   ├── base.py                 # BaseAgent with typed parsing & fallback
│   │   ├── file_reader.py          # Agent 1: FileReaderAgent
│   │   ├── coverage.py             # Agent 2: CoverageAgent (RAG + citations)
│   │   ├── risk_assessment.py      # Agent 3: RiskAssessmentAgent (fraud/total loss/BI)
│   │   ├── decision_drafter.py     # Agent 4: DecisionDraftAgent (4 outcomes)
│   │   ├── pipeline.py             # Adjudication pipeline orchestrator
│   │   └── schemas.py              # Strict Pydantic I/O models
│   ├── spine/                      # Deterministic code spine (M3)
│   │   ├── access_control.py       # Pre-agent entitlement checks
│   │   ├── date_engine.py          # Policy effective date verification
│   │   ├── financial_engine.py     # Deductibles & monetary calculations
│   │   ├── audit_logger.py         # Append-only immutable audit trail
│   │   ├── context.py              # SpineContext struct
│   │   └── orchestrator.py         # Pre-agent invariant coordinator
│   ├── retrieval/                  # Policy clause retrieval engine (M3)
│   │   └── policy_index.py         # Searchable BM25 corpus & citation grounding
│   ├── api/                        # FastAPI REST Service (M3)
│   │   └── app.py                  # Endpoints: /health, /adjudicate, /claims
│   ├── contracts/                  # Pydantic v2 client contracts (M2)
│   └── models/                     # Canonical synthetic data shapes (M2)
├── infra/                          # Terraform Infrastructure as Code (M2)
├── data/fixtures/                  # 20 validated synthetic claim dossiers
├── evals/
│   ├── run_pipeline_evals.py       # CI evaluation gate runner (M3)
│   └── cases/milestone1_cases.json # Evaluation cases
├── tests/                          # Automated Pytest suite (21 passing tests)
├── .github/workflows/ci.yml        # CI pipeline blocking image push on eval gate (M3)
├── Dockerfile                      # Production multi-stage Dockerfile (M3)
├── docker-compose.yml              # Single-command local orchestration (M3)
├── requirements.txt                # Pinned dependencies
├── DECISIONS.md                    # Architectural decision records (ADRs 001–010)
└── README.md                       # This file
```

---

## Milestone Progress

- [x] **M1 — Discovery & Scoping** (Week 1)
  - [x] Engagement charter (`docs/charter.md`)
  - [x] Stakeholder map & RACI (`docs/raci.md`)
  - [x] Four quantified success criteria (`docs/success-criteria.md`)
  - [x] DECISIONS.md with 5 dated ADRs
  - [x] 20 evaluation cases including adversarial families (`evals/cases/`)
- [x] **M2 — Design, Pricing & Architecture** (Week 2)
  - [x] Statement of Work (2-page contract) (`docs/sow.md`)
  - [x] Labeled architecture diagram & boundary justification (`docs/architecture.md`)
  - [x] Pricing model with assumptions stated (`docs/pricing.md`)
  - [x] Risk register of 6 risks anticipating later failures (`docs/risk-register.md`)
  - [x] Typed client contracts with idempotency rules (`src/contracts/`, `docs/contracts.md`)
  - [x] Synthetic data shapes & canonical fixtures (`src/models/`, `data/fixtures/`)
  - [x] Cloud provisioning evidence & Terraform IaC (`infra/`, `docs/cloud-provisioning.md`)
- [x] **M3 — Production Agents & CI Gate** (Week 3)
  - [x] 4-Agent adjudication set on OpenAI Agents SDK (`src/agents/`) with strict Pydantic schemas
  - [x] Searchable policy clause corpus with BM25 ranking & citation grounding (`src/retrieval/`)
  - [x] Deterministic spine pre-agent guards & financial engine (`src/spine/`)
  - [x] FastAPI REST service (`/health`, `/adjudicate`, `/claims/{id}/decisions`)
  - [x] Multi-stage Dockerfile & single-command local orchestration (`docker compose up`)
  - [x] GitHub Actions CI pipeline (`.github/workflows/ci.yml`) with automated evaluation gate
  - [x] All 4 decision outcomes correctly produced with explicit model vs fallback attribution
- [ ] **M4 — Integrate & Guard** (Week 4)
- [ ] **M5 — Handover** (Week 5)

---

## Evaluation Suite

Run the evaluation suite validator:

```bash
python evals/run_evals.py
```

### Case Distribution (Milestone 1: 20 cases)

| Decision | Count | Includes |
|----------|-------|----------|
| Approve | 6 | Standard approvals + prompt injection resistance test |
| Deny | 5 | Lapsed policy, exclusions (racing, DUI), vehicle not scheduled, forced auto-decision resistance |
| Flag | 4 | Narrative contradiction, suspicious timing, staged accident, airbag inconsistency |
| Route | 3 | Total loss, bodily injury, specialist (classic vehicle) |

**Adversarial families covered:**
- Prompt injection (EVAL-016)
- Cross-record leakage (EVAL-017, EVAL-018)
- Forced auto-decision (EVAL-019)
- Narrative contradiction (EVAL-020)

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
