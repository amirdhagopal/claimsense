# ClaimSense AI — Commercial Pricing & Unit Economics Model

**Document Version:** 1.0 (Milestone 2 Deliverable)  
**Engagement:** Apex Motor Insurance Ltd  
**Prepared by:** Forward Deployed Engineering Practice  

---

## 1. Executive Summary & Cost Philosophy

ClaimSense AI delivers a radical economic transformation for motor claims adjudication:
* **Current manual cost:** **$35.25** per claim (47 minutes of manual adjuster time).
* **ClaimSense AI operating cost:** **$0.10** per claim (AWS cloud infrastructure + OpenAI LLM inference).
* **First-pass review efficiency:** Compresses manual review time by **74%** (from 47 min to 12 min), liberating ~2,450 adjuster hours per month.
* **Return on Investment (ROI):** Payback period of the initial $85,000 FDE engagement is **under 45 days** purely on labor capacity gains, excluding additional fraud leakage recovery.

---

## 2. Forward Deployed Engineering (FDE) Services Pricing

The five-week engagement is structured as a fixed-fee professional services contract delivered by an embedded engineering pod:

### 2.1 Staffing Model & Resource Allocation

| Role | Allocation | Blended Weekly Rate | 5-Week Total |
|---|:---:|:---:|:---:|
| **Lead Forward Deployed Engineer (FDE)** | 1.0 FTE (100%) | $11,000 / wk | $55,000 |
| **Cloud Infrastructure & Security Architect** | 0.25 FTE (25%) | $3,500 / wk | $17,500 |
| **AI Evaluation & Quality Engineer** | 0.25 FTE (25%) | $2,500 / wk | $12,500 |
| **Total Professional Services** | **1.5 FTE** | **$17,000 / wk** | **$85,000** |

### 2.2 Milestone-Based Payment Schedule

Payments are tied strictly to verifiable delivery milestones:

| Milestone | Deliverable Trigger | Percentage | Amount (USD) |
|---|---|:---:|:---:|
| **Milestone 1 & 2** | Discovery, SoW, Architecture, Contracts, Checkpoint Sign-off | 30% | $25,500 |
| **Milestone 3 & 4** | Containerized Agent Pipeline, CI Evaluation Gate, Trust Boundary | 40% | $34,000 |
| **Milestone 5** | 150-Case Eval Suite, CloudWatch Dashboard, Incident Drill, Handover | 30% | $25,500 |
| **Total** | | **100%** | **$85,000** |

---

## 3. Operational Infrastructure Cost Model (AWS)

The production architecture is deployed on AWS in the `us-east-1` region using containerized serverless infrastructure designed for high availability and low operational overhead:

### 3.1 Monthly AWS Infrastructure Breakdown (Baseline 4,200 claims/month)

| AWS Resource | Sizing / Specification | Unit Cost Rate | Monthly Cost (USD) |
|---|---|---|:---:|
| **AWS ECS Fargate** | 2 Tasks × (1 vCPU, 2 GB RAM) active 24/7 (Multi-AZ) | $0.04048/vCPU-hr + $0.004445/GB-hr | $71.95 |
| **Application Load Balancer (ALB)** | 1 Regional ALB + 2 LCU average | $0.0225/ALB-hr + $0.008/LCU-hr | $27.90 |
| **Amazon ECR** | Container Image Storage (3 images × 1.2 GB) | $0.10 / GB-month | $0.36 |
| **Amazon S3** | Synthetic Docs & Policy Corpus (50 GB Standard) | $0.023 / GB-month | $1.15 |
| **AWS Secrets Manager** | 2 Secrets (OpenAI Key, JWT Secret) | $0.40 / secret-month | $0.80 |
| **AWS CloudWatch Logs** | Ingestion (12 GB/mo audit & app logs) + 90-day retention | $0.50 / GB ingested + $0.03 / GB archived | $6.90 |
| **AWS CloudWatch Metrics & Alarms** | 1 Dashboard + 5 Custom Metrics + 2 Alarms | $3.00/dashboard + $0.30/metric + $0.10/alarm | $4.70 |
| **AWS KMS** | 1 Customer Managed Key (CMK) for encryption at rest | $1.00 / key-month | $1.00 |
| **Data Transfer / Networking** | Inter-AZ traffic + NAT Gateway baseline | Bandwidth + NAT usage | $32.40 |
| **Total Monthly AWS Infrastructure** | | | **$147.16 / month** |

*Infrastructure Unit Cost per Claim (at 4,200 claims/mo):* **$0.035 per claim**.

---

## 4. Model Inference Cost Model (OpenAI API)

### 4.1 Token Consumption per Claim Across the 4-Agent Pipeline

Each claim traverses four specialized agents with structured inputs and outputs. Token consumption is modeled based on synthetic motor claim dossiers:

| Pipeline Step / Agent | Prompt / Input Tokens | Completion / Output Tokens | Primary Model |
|---|:---:|:---:|---|
| **Spine Context & Pre-Checks** | 0 (Code only) | 0 (Code only) | N/A (Compiled Python) |
| **Agent 1: FileReaderAgent** | 2,200 | 450 | `gpt-4o-mini` |
| **Agent 2: CoverageAgent (RAG)** | 3,400 | 500 | `gpt-4o` |
| **Agent 3: RiskAssessmentAgent** | 1,800 | 400 | `gpt-4o` |
| **Agent 4: DecisionDraftAgent** | 1,600 | 550 | `gpt-4o` |
| **Total Tokens per Claim** | **9,000 prompt tokens** | **1,900 completion tokens** | |

### 4.2 Inference Cost Calculation per Claim

Based on commercial OpenAI API rates:
* `gpt-4o`: $2.50 per 1M prompt tokens; $10.00 per 1M output tokens.
* `gpt-4o-mini`: $0.15 per 1M prompt tokens; $0.60 per 1M output tokens.

| Agent | Input Tokens | Input Cost | Output Tokens | Output Cost | Total Agent Cost |
|---|:---:|:---:|:---:|:---:|:---:|
| **FileReaderAgent** (`gpt-4o-mini`) | 2,200 | $0.00033 | 450 | $0.00027 | $0.00060 |
| **CoverageAgent** (`gpt-4o`) | 3,400 | $0.00850 | 500 | $0.00500 | $0.01350 |
| **RiskAssessmentAgent** (`gpt-4o`) | 1,800 | $0.00450 | 400 | $0.00400 | $0.00850 |
| **DecisionDraftAgent** (`gpt-4o`) | 1,600 | $0.00400 | 550 | $0.00550 | $0.00950 |
| **Total Model Cost per Claim** | **9,000** | **$0.01733** | **1,900** | **$0.01477** | **$0.03210** |

*Adding 25% safety buffer for retries and prompt iteration:* **$0.040 per claim**.

---

## 5. Total Cost of Ownership (TCO) & Unit Economics

| Cost Component | Monthly Cost (4,200 claims) | Cost per Claim |
|---|:---:|:---:|
| **AWS Cloud Infrastructure** | $147.16 | $0.035 |
| **OpenAI API Inference (with buffer)** | $168.00 | $0.040 |
| **Observability & Log Archival** | $15.00 | $0.004 |
| **Ongoing Maintenance Reserve** | $84.00 | $0.020 |
| **Total Operating Cost** | **$414.16 / month** | **$0.099 (~$0.10) per claim** |

---

## 6. Return on Investment (ROI) and Business Case

### 6.1 Baseline vs. Co-Pilot Efficiency Comparison

| Dimension | Current Baseline (Manual) | With ClaimSense AI Co-Pilot | Impact / Savings |
|---|---|---|---|
| **Time per First Pass** | 47 minutes | 12 minutes (Adjuster review + confirm) | **-74.5%** (-35 min/claim) |
| **Total Monthly Adjuster Hours** | 3,290 hours | 840 hours | **2,450 hours saved / month** |
| **Effective Cost per Claim** | $35.25 ($45/hr fully burdened) | $9.00 (Adjuster) + $0.10 (AI) = $9.10 | **$26.15 saved per claim** |
| **Monthly Labor Value Released** | — | — | **$110,250 / month** |
| **Annualized Operational Value** | — | — | **$1,323,000 / year** |

### 6.2 Fraud Leakage Reduction Impact

* Apex Motor Insurance pays ~$8,400,000 annually in motor physical damage indemnity.
* Industry fraud leakage is estimated at 3% ($252,000 annually).
* ClaimSense AI's multi-document narrative consistency checking detects subtle staged accidents and timing anomalies that bypass simple score thresholds.
* A conservative 15% improvement in fraud interception yields an additional **$37,800 annual recovery**.

### 6.3 Payback Period

$$\text{Payback Period} = \frac{\text{Fixed Implementation Fee (\$85,000)}}{\text{Net Monthly Labor Savings (\$110,250) - Monthly Operating Cost (\$414)}} = \frac{\$85,000}{\$109,836} \approx \mathbf{0.77 \text{ months (23 business days)}}.$$

---

## 7. Underlying Assumptions

1. **Volume:** Apex claims intake remains between 3,800 and 4,500 claims/month.
2. **Staffing Costs:** Licensed claims adjuster fully burdened labor rate is assumed at $45.00 USD/hour ($93,600 annualized salary + benefits).
3. **Model Rates:** OpenAI commercial pricing remains stable; token counts assume English synthetic claims with average document lengths of 3 pages.
4. **Human Review Time:** The licensed adjuster spends an average of 10–12 minutes reviewing the co-pilot dossier, verifying citations, and confirming the write-back.
5. **No Long-Term Commitments:** AWS pricing is based on standard On-Demand pricing without requiring 1-year or 3-year Savings Plans (further 20–30% AWS savings achievable via Compute Savings Plans).
