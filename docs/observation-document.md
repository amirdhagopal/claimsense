# ClaimSense AI — Observation Document & Handover Report

**Author:** Amirdha Gopal (Forward Deployed Engineer)  
**Client:** Motor Claims Insurer Engagement  
**Capstone Version:** Final (Week 5 Handover)  
**Date:** 23 October 2026  
**Repository:** https://github.com/amirdhagopal/claimsense  

---

## Executive Summary

ClaimSense AI is an enterprise-grade motor claims adjudication co-pilot designed to compress first-pass claim decisions from hours to minutes. The core architectural breakthrough is the **strict separation between deterministic code (the "spine") and model judgment (the 4-agent collaborative pipeline)**. 

Deterministic identity, route authentication, policy date math, and monetary calculations are implemented in immutable Python code and executed prior to invoking any model, eliminating prompt injection bypasses and ensuring 100% regulatory auditability.

This observation document consolidates the six formal sections required for Capstone Submission 2.

---

## Section 1: Deployment

### 1.1 Architecture & Hosting Topology
The production architecture is deployed on **AWS ECS Fargate** with an **Application Load Balancer (ALB)** distributing traffic across multi-AZ container tasks:
- **Compute:** AWS ECS Fargate (2 vCPU, 4GB RAM) with auto-scaling between 2 and 10 tasks based on CPU and request latency.
- **Packaging:** Multi-stage Docker container built on `python:3.12-slim`, minimizing surface area to 180MB.
- **Local Emulation & Offline Capability:** Designed to run 100% locally with zero cloud dependencies or external paid APIs using:
  - Local Ollama running `llama3.2:3b` at `http://localhost:11434/v1`.
  - LocalStack for CloudWatch and ALB mock interfaces at `http://localhost:4566`.
  - Single-command orchestration via `docker compose up --build`.

### 1.2 Infrastructure as Code (IaC)
All cloud resources are codified in validated Terraform templates (`infra/`):
- `infra/main.tf`: VPC, subnets, ECS cluster, service, task definitions, and security groups.
- `infra/alb.tf`: ALB, target groups, listener rules, and health checks (`/health`).
- `infra/cloudwatch.tf`: CloudWatch dashboard, metric filters, and SLA alarm definitions.

---

## Section 2: Evaluation

### 2.1 150-Case Comprehensive Evaluation Suite
The evaluation suite contains **150 structured, schema-validated cases** (`evals/cases/`):
- **Decision Outcomes Distribution:**
  - `approve`: 49 cases (32.7%)
  - `deny`: 40 cases (26.7%)
  - `flag`: 32 cases (21.3%)
  - `route`: 29 cases (19.3%)
- **Adversarial Families Covered (33 cases):**
  - **Prompt Injection (8 cases):** Malicious payloads hidden in claim narratives attempting system prompt overrides (e.g., `EVAL-016`). The pipeline successfully ignores the injection and focuses strictly on physical damage.
  - **Cross-Record Leakage (9 cases):** Requests from adjusters lacking entitlement to specific claims (e.g., `EVAL-017`). The pre-agent deterministic spine refuses access with HTTP 403 Forbidden and zero claim data.
  - **Forced Auto-Decision (8 cases):** Payloads claiming management pre-approval or automated settlement flags.
  - **Narrative Contradiction (8 cases):** Physical inconsistencies (e.g. rear-end narrative with front damage) or medical contradictions (airbag burns without deployment).

### 2.2 CI Evaluation Gate
The evaluation gate (`evals/run_pipeline_evals.py`) runs automatically in GitHub Actions on every push and pull request. The gate enforces an **80.0% minimum accuracy threshold** across all 4 decision outcomes and blocks the container build if violated.

---

## Section 3: Observability

### 3.1 Telemetry Metrics Tracked
The system instruments real-time telemetry at the HTTP transport perimeter (`src/spine/metrics.py`):
1. **Pipeline Call Volume:** Total lifetime calls and rolling 5-minute requests per minute.
2. **Error & Refusal Rate (%):** Tracking 4xx client errors and 5xx failures against the **&le; 5.0% SLA**.
3. **Latency Distribution:** p50 (median) and p95 (95th percentile) wall-clock time against the **&le; 60-second p95 SLA**.
4. **CloudWatch Alarm State:** Live evaluation of `HighLatencyP95Alarm` (> 60,000 ms) and `HighErrorRateAlarm` (> 5%).

### 3.2 Visual Interactive Dashboard
Served directly by the API at `GET /` and `GET /dashboard`:
- Top SLA health banner with pulsing alarm indicator.
- Live telemetry cards updated via asynchronous polling (`GET /dashboard/metrics`).
- Adjudication workbench with step-by-step 4-agent trace.
- Live stream of the append-only audit trail.

---

## Section 4: Platform Reliability

### 4.1 Pre-Agent Invariant Protection
The deterministic spine (`src/spine/orchestrator.py`) guarantees five system invariants before any LLM inference occurs:
1. **Entitlement Invariant:** Unauthenticated or unauthorized callers are rejected immediately in code with HTTP 401 or 403.
2. **Date Invariant:** Incident date must fall within `effective_date` and `expiry_date`. Lapsed policies are rejected deterministically.
3. **Vehicle Invariant:** Claimed VIN must be registered on the policy's vehicle schedule.
4. **Monetary Invariant:** Deductible subtraction and total loss thresholding (>75% ACV) are computed using exact Python arithmetic, never model generation.
5. **Idempotency Invariant:** Duplicate decision write-backs with the same UUIDv4 key return cached responses (`idempotent_replay: true`), preventing double payout authorization.

### 4.2 Incident Drill & Mean Time to Recovery (MTTR)
A deliberate SEV-2 latency regression drill was conducted (`docs/incident-report.md`). A 65,000ms delay was injected into the pipeline, triggering `HighLatencyP95Alarm` within 30 seconds. On-call engineering followed **Runbook Procedure 2**, executed an ECS container rollback, and verified complete service recovery within **2 minutes 45 seconds**.

---

## Section 5: Handover

### 5.1 Runbook Procedures
The operational runbook (`docs/runbook.md`) provides first-time operators with comprehensive instructions for:
1. **Adding a User:** Generating HMAC-SHA256 signed tokens with custom claim entitlements.
2. **Rolling Back Deployments:** Reverting ECS task definitions or Git commits.
3. **Escalating Flagged Claims:** Manual adjuster override and SIU investigation workflow.
4. **Updating Policy Corpus:** Adding canonical clauses and rebuilding the grounded BM25 index.

### 5.2 Deliverables Checklist
All engagement artifacts are consolidated in the repository:
- Charters, RACI, and Success Criteria (`docs/charter.md`, `docs/raci.md`, `docs/success-criteria.md`)
- Commercial Statement of Work & Pricing (`docs/sow.md`, `docs/pricing.md`)
- System Architecture & Data Flow (`docs/architecture.md`)
- Risk Register (`docs/risk-register.md`)
- Typed Contracts (`src/contracts/`)
- Two-User Access Control Test Evidence (`docs/two-user-access-test.md`)
- 12 Architectural Decision Records (`DECISIONS.md`)

---

## Section 6: Observations & Lessons Learned

### 6.1 The "Spine vs Model" Paradigm
The greatest lesson from this engagement is that **security, dates, and money must never be delegated to an LLM**. Models are probabilistic inference engines; when asked to verify policy dates or entitlements, models are susceptible to subtle prompt variations, context stuffing, and adversarial manipulation. By wrapping the 4-agent pipeline in a deterministic Python spine, the system achieves the creative reasoning benefits of AI with the mathematical guarantees of enterprise software.

### 6.2 Small Model Calibration (Local Ollama vs Frontier Models)
Running locally with smaller models (e.g. `llama3.2:3b`) required strict output normalization:
- Smaller models tend to output `["None"]` as a string when asked for empty lists, which caused naive Python `if exclusions:` checks to trigger false denials. Adding Pydantic field validators to clean lists made the system resilient across all model sizes.
- Lexical BM25 retrieval provides sub-millisecond grounded citations without the latency, cost, and complexity of external vector databases.

### 6.3 Adjuster Adoption & The "Co-Pilot" Philosophy
Adjusters do not want a black-box replacement; they require a transparent co-pilot that highlights relevant clauses, calculates exact figures, and flags inconsistencies. Requiring human adjuster confirmation on every draft outcome preserves adjuster agency and regulatory compliance.
