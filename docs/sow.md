# ClaimSense AI — Statement of Work (SoW)

**Project Name:** ClaimSense AI — Motor Claims Adjudication Co-Pilot  
**Engagement Type:** Forward Deployed Engineering (FDE) Professional Services  
**Client:** Apex Motor Insurance Ltd ("Client")  
**Service Provider:** Forward Deployed Engineering Practice ("Provider")  
**Effective Date:** 2 October 2026  
**Document Version:** 1.0 (Milestone 2 Deliverable)  

---

## 1. Project Background and Executive Summary

Apex Motor Insurance Ltd processes approximately 4,200 motor claims monthly across three siloed systems: Claims Management System (CMS), Document Store (DocStore), and Policy Administration (PolicyAdmin). The current adjudication process is entirely manual, averaging 47 minutes per first-pass decision, suffering from high inter-adjuster variance, lacking auditable reasoning trails, and relying on blunt numerical thresholds for fraud detection rather than document-level narrative analysis.

This Statement of Work defines the five-week client engagement to design, build, test, secure, and deploy **ClaimSense AI**—a motor claims adjudication co-pilot powered by the OpenAI Agents SDK and bounded by an immutable deterministic code spine. The co-pilot delivers structured first-pass recommendations (Approve, Flag/Refer, Route, Deny) with grounded policy citations in under 60 seconds, with every final outcome confirmed by a licensed human adjuster.

---

## 2. Scope of Work

### 2.1 In-Scope Deliverables

The Provider shall design, implement, containerise, and deploy the following components:

1. **Deterministic Spine (Code-Enforced Boundary):**
   - Pre-agent authentication, identity verification, and role-based / claim-level entitlement checks.
   - Deterministic policy effective date validation (`incident_date` vs `[effective_date, expiry_date]`) executed in compiled Python code, never delegated to a language model.
   - Deterministic financial arithmetic (payout computation, deductible application, total-loss threshold comparison).
   - Immutable audit logging recording every inbound call (`{user_id, action, resource_id, timestamp, outcome}`).

2. **Multi-Agent Adjudication Pipeline (OpenAI Agents SDK):**
   - `FileReaderAgent`: Ingests and cross-references claim metadata, repair estimates, police reports, and witness narratives to identify contradictions.
   - `CoverageAgent`: Performs semantic retrieval over the PolicyAdmin clause corpus, verifying coverage grants and exclusions, and strictly attributing judgments to immutable clause IDs (e.g., `CLS-PER-006`, `CLS-EXC-003`).
   - `RiskAssessmentAgent`: Evaluates narrative consistency, indicators of staged accidents or timing anomalies, total loss economics, and severe bodily injury exposure.
   - `DecisionDraftAgent`: Synthesizes upstream agent findings into a strictly typed adjudication dossier featuring one of four standardized recommendations: **Approve**, **Flag/Refer**, **Route**, or **Deny**.

3. **Client System Integration Adapters:**
   - Typed REST client contracts for CMS, DocStore, and PolicyAdmin with automated request validation.
   - Idempotent decision write-back protocol (`POST /claims/{claim_id}/decisions`) supporting deduplication keys and conflict resolution.

4. **Human-in-the-Loop Adjuster Interface:**
   - Web interface enabling licensed adjusters to review claims, inspect extracted facts and clause citations, confirm recommendations, or submit overrides.

5. **Cloud Deployment, Observability, and Handover:**
   - Fully containerised stack orchestrated for AWS deployment (ECS Fargate, ALB, CloudWatch).
   - Operational dashboard reporting error rates, invocation volume, and p95 latency with active CloudWatch alarms.
   - Automated CI evaluation gate blocking deployments on accuracy or safety regressions.
   - Comprehensive incident drill report and operational runbook.

### 2.2 Out-of-Scope Items

The following activities are expressly excluded from this engagement:
- Live integration with Client's production networks or proprietary mainframe systems during the FDE phase (all work utilizes high-fidelity synthetic contracts).
- Fully autonomous claim settlement or automated financial disbursement without human confirmation.
- Direct claimant-facing communication, conversational chatbots, or automated denial letter dispatch.
- Fine-tuning or pre-training proprietary foundation model weights.
- Ingestion or processing of real Personally Identifiable Information (PII) or non-synthetic production data.

---

## 3. Acceptance Criteria for Delivered System

In accordance with Section 6 of the Capstone Brief, the delivered system must satisfy all five criteria below, each demonstrable by an independent first-time operator working solely from the deployed system and documentation:

| # | Criterion | Verification Method | Pass Threshold |
|---|-----------|---------------------|----------------|
| **AC-1** | **Decision on any claim** | Any valid claim in the synthetic corpus returns a first decision (`Approve`, `Flag`, `Route`, `Deny`), accompanied by auditable reasoning and verifiable clause citations. | 100% of valid claims processed produce structured verdicts with valid clause references. |
| **AC-2** | **Refusal on entitlement** | Requests initiated by a user lacking authorization for the requested claim are immediately refused with zero claim data returned; refusal is logged in the audit trail. | Zero unauthorized data leakage across test suites; 100% denial rate on unauthorized attempts. |
| **AC-3** | **Attribution within a response** | In every response, model-generated judgment is explicitly distinguishable from deterministic computation through structured schema boundaries. | 100% schema separation between deterministic spine fields and agent outputs. |
| **AC-4** | **Reproducible evidence** | The automated evaluation suite (including adversarial injection, cross-record leakage, and forced auto-decision tests) executes on the submitted commit and passes the CI gate. | Evaluation gate passes with accuracy ≥90% and 0% adversarial bypass. |
| **AC-5** | **Operability without the author** | An independent operator can deploy the stack from documentation, observe live metrics on the dashboard, execute runbook procedures, and recover from an induced failure. | Successful execution of the four runbook procedures and incident drill recovery without developer intervention. |

---

## 4. Intellectual Property and Data Handling Terms

### 4.1 Intellectual Property (IP) Rights
1. **Client Work Product:** All custom configuration files, synthetic dataset generation scripts, prompt templates, agent orchestration code, CI/CD pipelines, and documentation developed specifically under this engagement shall become the exclusive property of the Client upon final payment.
2. **Background Technology:** The Provider retains all rights to its pre-existing core libraries, scaffolding tools, and general knowledge. The Provider grants the Client a perpetual, irrevocable, royalty-free, worldwide license to utilize all background IP embedded in the deliverables.
3. **Foundation Models:** Third-party model weights and APIs (OpenAI) remain the intellectual property of their respective providers and are governed by their commercial terms of service.

### 4.2 Data Handling and Privacy Terms
1. **Synthetic Data Mandate:** Under no circumstances shall production policyholder data, real motor claim files, or Personally Identifiable Information (PII) be introduced into the environment. 100% of data used in development, testing, and evaluation is synthetic.
2. **Model Provider Data Governance:** All interactions with OpenAI APIs shall utilize commercial enterprise endpoints where data is explicitly excluded from foundation model training and fine-tuning.
3. **Data Retention & Ephemerality:** Claim files and agent scratchpads processed by ClaimSense AI shall remain ephemeral in memory during pipeline execution, persisting only structured decision summaries and audit records to secure storage.
4. **Security & Encryption:** All data in transit shall be encrypted using TLS 1.3. All data at rest (audit logs, evaluation fixtures, container images) shall be encrypted using AES-256 via AWS KMS-managed keys.

---

## 5. Five-Week Timeline and Milestones

| Week | Milestone Name | Key Deliverables & Checkpoints | Target Date |
|------|----------------|--------------------------------|-------------|
| **Week 1** | **Discovery & Scoping** | Engagement Charter; Stakeholder Map & RACI; 4 Quantified Success Criteria; Initial `DECISIONS.md`; 20 Evaluation Cases. | 1 Oct 2026 ✅ |
| **Week 2** | **Design, Pricing & Architecture** | 2-Page SoW; Complete Architecture Diagram; Pricing Model; 5-Risk Register; Typed Client Contracts; Synthetic Data Shapes; Cloud Account Evidence. <br/>*Checkpoint: Submission 1.* | 8 Oct 2026 |
| **Week 3** | **Production Agents & CI Gate** | OpenAI Agents SDK implementation; Local container orchestration; Policy retrieval with clause citations; CI evaluation gate; 4-outcome verification. | 15 Oct 2026 |
| **Week 4** | **Integration & Trust Boundary** | Data access boundary deployed; Route-level auth; Code-enforced access control; 2-user isolation test; Complete immutable audit trail. | 22 Oct 2026 |
| **Week 5** | **Evaluation, Handover & Exit** | 150-case evaluation suite (adversarial families); CloudWatch dashboard & alarm; Incident drill & report; 4-procedure runbook; Client presentation & demo. <br/>*Final: Submission 2.* | 29 Oct 2026 |

---

## 6. Commercial Terms and Payment Schedule

The engagement is priced on a fixed-fee milestone basis totaling **$85,000 USD**, payable against verified milestone sign-offs:

| Milestone / Deliverable | Milestone Percentage | Amount (USD) | Due Condition |
|-------------------------|----------------------|--------------|---------------|
| Milestone 1 & 2 Sign-off (Checkpoint) | 30% | $25,500 | Submission 1 checkpoint acceptance |
| Milestone 3 & 4 Delivery (Working Stack) | 40% | $34,000 | Containerized agents + trust boundary verified |
| Milestone 5 Handover & Presentation | 30% | $25,500 | Submission 2 final acceptance & live demo |
| **Total Engagement Value** | **100%** | **$85,000** | |

---

## 7. Signatures and Authorization

IN WITNESS WHEREOF, the parties hereto have executed this Statement of Work through their authorized representatives as of the date first written above.

**For Apex Motor Insurance Ltd (Client):**  
Name: *Marcus Vance*  
Title: *Head of Claims Operations*  
Signature: ___________________________ Date: ______________  

**For ClaimSense AI Practice (Forward Deployed Engineering):**  
Name: *Amirdha Gopal*  
Title: *Lead Forward Deployed Engineer*  
Signature: ___________________________ Date: ______________  
