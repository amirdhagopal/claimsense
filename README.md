# ClaimSense AI

A claims adjudication co-pilot that compresses first-pass claim decisions from hours to minutes — with reasoning recorded, evidence cited, and a licensed adjuster accountable for every outcome.

**Engagement:** Five-week FDE capstone · AWS + OpenAI Agents SDK
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
│   ├── charter.md              # Engagement charter (M1)
│   ├── raci.md                 # Stakeholder map & RACI (M1)
│   └── success-criteria.md     # Four quantified success criteria (M1)
├── evals/
│   ├── schema.json             # Evaluation case JSON schema
│   ├── run_evals.py            # Evaluation suite runner
│   └── cases/
│       └── milestone1_cases.json  # 20 initial evaluation cases (M1)
├── DECISIONS.md                # Architectural decision records (M1)
└── README.md                   # This file
```

---

## Milestone Progress

- [x] **M1 — Discovery & Scoping** (Week 1)
  - [x] Engagement charter (`docs/charter.md`)
  - [x] Stakeholder map & RACI (`docs/raci.md`)
  - [x] Four quantified success criteria (`docs/success-criteria.md`)
  - [x] DECISIONS.md with 5 dated ADRs
  - [x] 20 evaluation cases including adversarial families (`evals/cases/`)
- [ ] **M2 — Design & SoW** (Week 2)
- [ ] **M3 — Build Agents** (Week 3)
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
