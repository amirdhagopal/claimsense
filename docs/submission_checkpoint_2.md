# ClaimSense AI — Checkpoint 2 (Final Capstone) Submission Document

**Participant Name:** Amirdha Gopal Rajendran  
**Cohort Name:** Forward Deployed Engineering LevelUp Program - Mid-August 2026  
**Tech Stack:** AWS + OpenAI Agents SDK / Ollama + Python 3.12 (FastAPI) + Docker + Terraform + Vanilla Web UI  
**Submission Type:** Checkpoint - 2 (Final Submission: Milestones 1 through 5)  
**Date:** 23 October 2026  
**Final Release Tag:** `v1.0.0`  
**Repository URL:** https://github.com/amirdhagopal/claimsense  

---

## 1. Executive Summary & Required Assets

This document certifies the successful completion of all five milestones of the **ClaimSense AI** Motor Claims Adjudication Co-Pilot capstone project for *Apex Motor Insurance Ltd*.

### Three Required Submission Assets:

| Asset | Location / Value | Description |
| :--- | :--- | :--- |
| **Asset 1: Final Codebase** | https://github.com/amirdhagopal/claimsense <br/>Tag: `v1.0.0` (commit `bcffc18`) | Full production repository containing deterministic spine, 4-agent pipeline, BM25 retrieval, Docker container, Terraform IaC, route auth, and 39 passing unit tests. |
| **Asset 2: Observation Document** | [`docs/observation-document.md`](https://github.com/amirdhagopal/claimsense/blob/main/docs/observation-document.md) | Comprehensive 6-section formal report analyzing deployment readiness, 150-case evals, observability, platform reliability, operational handover, and key architectural lessons. |
| **Asset 3: Deployed Frontend + Demo** | Frontend: `http://localhost:8000/dashboard` <br/>Demo Script: [`docs/presentation.md`](https://github.com/amirdhagopal/claimsense/blob/main/docs/presentation.md) | Single-page glassmorphic adjuster co-pilot application featuring real-time adjudication, BM25 legal citations, adjuster override/write-back, and live CloudWatch telemetry. |

---

## 2. Asset 1: Final Codebase Verification

* **Repository:** `https://github.com/amirdhagopal/claimsense`
* **Release Tag:** `v1.0.0`
* **Local Test Suite:** 39 passed in 18.31s (`PYTHONPATH=. pytest tests/ -v`)
* **Evaluation Suite:** 150/150 cases passed schema validation and automated benchmark checks (`python3 evals/run_evals.py`)

### Git History Milestone Trace:
1. `3b4e914`: Milestone 1 — Discovery, Charter, RACI, Success Criteria, 20 Baseline Cases.
2. `f23555f`: Milestone 2 — Statement of Work, Pricing & Unit Economics, Typed Contracts, Terraform IaC.
3. `1431b73`: Milestone 3 — 4-Agent Pipeline, BM25 Retrieval, Deterministic Spine, Docker, CI Gate.
4. `7c09fd7`: Milestone 4 — Route-Level Bearer Auth, Two-User Access Control Isolation Test, Audit Trail.
5. `bcffc18`: Milestone 5 — 150-Case Evals, Operational Dashboard, Runbook, Incident Report, Tag `v1.0.0`.

---

## 3. Asset 2: Completed Observation Document Summary

The complete observation document is checked into [`docs/observation-document.md`](https://github.com/amirdhagopal/claimsense/blob/main/docs/observation-document.md). Key findings across its 6 required sections include:

1. **Production Deployment & Readiness Assessment:**
   * Validated containerized FastAPI service on ECS Fargate / local Docker.
   * Deterministic code boundary completely separates access control and date/money math from foundation models.
2. **Evaluation Suite Results & Performance Analysis:**
   * 150 ground-truth cases across all 4 outcomes (49 Approve, 40 Deny, 32 Flag, 29 Route).
   * 33 adversarial cases across 4 attack vectors (prompt injection, cross-record leakage, forced auto-decision, narrative contradictions) successfully blocked with 0% adversarial bypass.
3. **Observability, Telemetry & SLA Compliance:**
   * CloudWatch-compatible metric pipeline tracking total call volume, error rate, and p50/p95/p99 latencies.
   * SLA Alarms configured: `HighLatencyP95Alarm` (> 60s) and `HighErrorRateAlarm` (> 5%).
4. **Platform Reliability & Failure Modes (SEV-2 Incident Drill):**
   * Simulated an upstream model latency breach (> 60s p95) under load.
   * Alarm fired in 30 seconds; ECS auto-rollback initiated; system recovered to healthy state in **2 minutes 45 seconds MTTR**. Full report in [`docs/incident-report.md`](https://github.com/amirdhagopal/claimsense/blob/main/docs/incident-report.md).
5. **Operational Handover & Production Readiness:**
   * 4 detailed Standard Operating Procedures in [`docs/runbook.md`](https://github.com/amirdhagopal/claimsense/blob/main/docs/runbook.md):
     - SOP-01: Provisioning a New Claims Adjuster User.
     - SOP-02: Rolling Back a Production Deployment on AWS ECS.
     - SOP-03: Escalating a Fraud-Flagged Claim to SIU.
     - SOP-04: Updating the Policy Clause Corpus and Re-indexing BM25.
6. **Retrospective & Key Engineering Lessons Learned:**
   * Strict Pydantic contracts and deterministic code boundaries are essential in regulated domains.
   * Smaller models require explicit output sanitization (e.g. handling markdown fences and empty exclusion arrays).

---

## 4. Asset 3: Deployed Frontend & Demo Recording Guide

### 4.1 Deployed Web Co-Pilot URL
* **URL:** `http://localhost:8000/dashboard` (also accessible at root `http://localhost:8000/`)
* **Technology:** FastAPI backend serving an interactive, glassmorphic dark-mode web application (HTML5/CSS3/Vanilla JS).

### 4.2 Interactive Co-Pilot Capabilities
1. **Preset Claim Dossier Switcher:** Instant loading of standard collision claims (`CLM-2026-0101`), adversarial prompt injection attempts (`CLM-ADV-001`), cross-record leakage attempts (`CLM-ADV-002`), or total loss claims.
2. **One-Click Real-Time Adjudication:** Executes the 4-agent pipeline (`FileReader`, `Coverage`, `RiskAssessment`, `DecisionDrafter`) through the deterministic spine and displays token breakdown, BM25 retrieved clauses, and fraud risk score.
3. **Adjuster Override & Decision Write-Back:** Human adjusters can edit authorized payouts, enter adjuster rationale, and commit an idempotent decision record back to the system.
4. **Live Operational Telemetry:** Real-time polling of call volume, CPM, error rate, p50/p95 latencies, and CloudWatch SLA alarm status.
5. **Interactive Audit Log & Evals Viewer:** In-browser inspection of tamper-proof audit trails and the 150-case evaluation suite distribution.

### 4.3 Demo Walkthrough Sequence (for video/live demo)
1. **Step 1 (0:00 - 0:45):** Open `http://localhost:8000/dashboard`. Point out the system health badge and live CloudWatch telemetry metrics.
2. **Step 2 (0:45 - 1:30):** Select claim `CLM-2026-0101`. Click "Adjudicate Claim with ClaimSense AI". Show the deterministic spine passing in 1ms, followed by the 4 agents extracting facts, matching clause `CLS-PER-006` via BM25, and drafting an Approval.
3. **Step 3 (1:30 - 2:15):** In the Adjuster Write-Back panel, modify the authorized payout from $2,300 to $2,100, add the note "Adjusted labor rate based on regional tariff", and click "Confirm Decision". Show the confirmed badge and audit trail entry.
4. **Step 4 (2:15 - 3:00):** Select adversarial claim `CLM-ADV-001` (Prompt Injection). Run adjudication. Demonstrate how the system resists the injection and properly flags the claim.
5. **Step 5 (3:00 - 3:30):** Navigate to the Observability and Evaluation tabs to show live metrics and the 150-case benchmark.

---

## 5. Form Submission Fields Quick Reference

Use these values when completing the Google Form:

* **Name:** `Amirdha Gopal Rajendran`
* **Cohort Name:** `Forward Deployed Engineering LevelUp Program - Mid-August 2026`
* **Tech Stack Used:** `AWS + OpenAI Agents SDK / Ollama + Python 3.12 (FastAPI) + Docker + Terraform + Vanilla Web UI`
* **Select the Checkpoint submission:** `Checkpoint - 2`
* **Submission Link (Upload File):** Upload `docs/ClaimSense_AI_Checkpoint_2_Final_Submission.pdf` (compiled from this document).
