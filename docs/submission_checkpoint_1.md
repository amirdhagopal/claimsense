# ClaimSense AI — Checkpoint 1 Submission Document

**Participant Name:** Amirdha Gopal  
**Tech Stack:** AWS + OpenAI Agents SDK + Python 3.12 (FastAPI) + Docker + Terraform  
**Submission Type:** Checkpoint - 1 (Milestones 1 & 2)  
**Date:** 22 October 2026  

---

## 1. Capstone Repository URL

* **Repository Name:** `claimsense`
* **Local Git Branch:** `main` (Commits: `3b4e914` [Milestone 1], `f23555f` [Milestone 2])
* **GitHub Repository URL:** `https://github.com/[YOUR_GITHUB_USERNAME]/claimsense` *(Replace with your GitHub repo URL after pushing)*

---

## 2. Declaration of Completed Deliverables

### Milestone 1: Discovery & Scoping (Week 1) — 100% COMPLETE
- [x] **Engagement Charter (`docs/charter.md`):** Complete 2-page document naming the three client systems (CMS, DocStore, PolicyAdmin), integration points, core constraints, and 5-week schedule.
- [x] **Stakeholder Map & RACI Matrix (`docs/raci.md`):** 9 identified stakeholders with influence–interest matrix, engagement-level RACI, and per-claim runtime RACI.
- [x] **Four Quantified Success Criteria (`docs/success-criteria.md`):**
  1. Decision accuracy (Target: ≥90%, Minimum: ≥80%)
  2. Pipeline latency (Target: p50 ≤30s, p95 ≤60s)
  3. Adjuster confirmation rate (Target: ≥75%)
  4. Fraud routing accuracy (Precision ≥80%, Recall ≥85%)
- [x] **Architectural Decision Records (`DECISIONS.md`):** ADRs 001 through 005 establishing the pre-agent deterministic spine, four-agent pipeline, hierarchical clause taxonomy, eval-driven development, and append-only audit trail.
- [x] **Initial Evaluation Suite (`evals/cases/milestone1_cases.json`):** 20 comprehensive evaluation cases covering all 4 outcomes (7 approve, 6 deny, 4 flag, 3 route) and 5 adversarial cases (prompt injection, cross-record leakage ×2, forced auto-decision, narrative contradiction).
- [x] **Evaluation Runner (`evals/run_evals.py`):** Schema-validated runner verifying case distribution.

### Milestone 2: Statement of Work, Pricing & Architecture (Week 2) — 100% COMPLETE
- [x] **Statement of Work (`docs/sow.md`):** 2-page formal contract covering scope, acceptance criteria (AC-1 through AC-5), intellectual property, synthetic data governance, 5-week timeline, and $85,000 milestone fee structure.
- [x] **System Architecture & Data Flow (`docs/architecture.md`):** Full Mermaid architecture diagram with 16 labeled data flows, explicit deterministic spine vs. model judgment boundary justification, and 4 evaluated/discarded alternatives.
- [x] **Commercial Pricing & Unit Economics (`docs/pricing.md`):** Staffing rates, AWS monthly infrastructure breakdown ($147.16/mo), per-agent OpenAI token consumption model ($0.040/claim), total cost ($0.10/claim vs. $35.25 manual), and a 23-day ROI payback calculation.
- [x] **Risk Register (`docs/risk-register.md`):** 6 detailed risks anticipating later failures (prompt injection, cross-record leakage, stale policy data vs. lapsed dates, latency/quota limits, hallucinated citations, and deployment regressions) with 5×5 scoring and mitigations.
- [x] **Typed Client System Contracts (`src/contracts/`, `docs/contracts.md`):** Strongly-typed Pydantic v2 schemas for CMS, DocStore, and PolicyAdmin with UUIDv4 idempotency rules, SHA-256 payload fingerprinting, and conflict handling.
- [x] **Synthetic Data Shapes & Canonical Fixtures (`src/models/`, `data/fixtures/`):** Motor policy clause catalog (`CLS-XXX-###`) and 20 validated synthetic claim dossiers.
- [x] **Cloud Account Provisioning & Terraform IaC (`infra/`, `docs/cloud-provisioning.md`):** Complete Terraform configuration for AWS ECS Fargate, ALB, ECR, CloudWatch Dashboard & Alarms, validated via `terraform validate`.
- [x] **Architectural Decisions (`DECISIONS.md`):** ADRs 006, 007, and 008 added for idempotency, Pydantic v2 contracts, and serverless container architecture.

---

## 3. Environment Readiness & Execution Evidence

The project environment is verified and operational:
* **Python Runtime:** Python 3.12+ with Pydantic v2, FastAPI, and Pytest.
* **Contract Verification:** All contract unit tests pass with zero errors.
* **Evaluation Suite:** All 20 evaluation cases pass schema validation and outcome distribution checks.
* **Terraform IaC:** Initialized and validated with HashiCorp AWS Provider v5.100.0.

### Execution Log Summary:
```text
$ PYTHONPATH=. pytest tests/ -v
======================== 5 passed in 0.10s =========================
tests/test_contracts.py::test_claim_record_validation PASSED
tests/test_contracts.py::test_claim_record_invalid_id PASSED
tests/test_contracts.py::test_decision_request_idempotency_key_validation PASSED
tests/test_contracts.py::test_policy_deterministic_date_math PASSED
tests/test_contracts.py::test_clause_citation_regex PASSED

$ python3 evals/run_evals.py
============================================================
EVALUATION SUITE — CASE DISTRIBUTION
Total cases: 20
By decision outcome: approve: 7, deny: 6, flag: 4, route: 3
By category: standard: 15, adversarial: 5
Adversarial families: cross_record_leakage: 2, prompt_injection: 1,
                      forced_auto_decision: 1, narrative_contradiction: 1
============================================================

$ cd infra && terraform validate
Success! The configuration is valid.
```

---

## 4. Statement of Outstanding Blockers

* **Technical / Design Blockers:** **NONE.** All architectural, scoping, contract, and evaluation deliverables for Milestones 1 and 2 are fully in place.
* **Account / Credential / Quota Status:**
  - OpenAI API key and AWS environment credentials are ready for activation in Milestone 3 (Agent development).
  - Terraform infrastructure templates are validated and ready to provision ECS Fargate and CloudWatch resources during deployment.
  - The stack is fully prepared for Milestone 3 (OpenAI Agents SDK implementation and CI evaluation gate).
