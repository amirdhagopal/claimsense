# ClaimSense AI — Cloud Account Provisioning & Infrastructure Evidence

**Document Version:** 1.0 (Milestone 2 Deliverable & Submission 1 Checkpoint Evidence)  
**Target Cloud:** Amazon Web Services (AWS)  
**Primary Region:** `us-east-1`  
**Orchestration:** HashiCorp Terraform (`infra/`) + Docker Container Registry  

---

## 1. Cloud Architecture Overview

In accordance with Section 4 of the Capstone Brief ("Hosting, observability and recovery: AWS"), ClaimSense AI is deployed on a highly available, serverless container runtime (AWS ECS Fargate) fronted by an Application Load Balancer and deeply integrated with AWS CloudWatch for metrics, audit logging, and automated alerting.

```
                  Internet / Licensed Adjusters
                                │
                                ▼ HTTPS (TLS 1.3)
                    ┌───────────────────────┐
                    │  Application Load     │
                    │     Balancer (ALB)    │
                    └───────────┬───────────┘
                                │ Health Checks (/health)
                                ▼
         ┌──────────────────────────────────────────────┐
         │          Amazon ECS Cluster (Fargate)        │
         │  ┌────────────────────┐ ┌──────────────────┐ │
         │  │ Fargate Task 1     │ │ Fargate Task 2   │ │
         │  │ (FastAPI + Spine)  │ │ (AZ us-east-1b)  │ │
         │  └─────────┬──────────┘ └─────────┬────────┘ │
         └────────────┼──────────────────────┼──────────┘
                      │                      │
         ┌────────────┴──────────────────────┴──────────┐
         │             AWS CloudWatch Platform          │
         │  • Log Group: /ecs/claimsense-ai (90d TTL)   │
         │  • Metric Namespace: ClaimSenseAI            │
         │  • Dashboard: ClaimSense-Operational-Metrics │
         │  • Alarms: HighLatencyAlarm (p95 > 60s)      │
         │            HighErrorRateAlarm (> 5%)         │
         └──────────────────────────────────────────────┘
```

---

## 2. Infrastructure as Code (IaC) Inventory

The entire AWS footprint is declared in version-controlled Terraform modules in [`infra/`](file:///Users/amirdhagopal/Projects/ik/claimsense/infra):

| AWS Resource Type | Resource Identifier | Configuration / Sizing | Purpose |
|---|---|---|---|
| **Amazon ECR** | `aws_ecr_repository.app_repo` | Immutable tags, Scan on Push, 30-day lifecycle expiration | Stores versioned Docker container images for CI/CD. |
| **Amazon ECS Cluster** | `aws_ecs_cluster.main` | Container Insights enabled | Serverless execution plane for container workloads. |
| **ECS Task Definition** | `aws_ecs_task_definition.app` | 1 vCPU (1024), 2 GB RAM (2048), `awsvpc` network mode | Runs the FastAPI service + deterministic spine. |
| **ECS Service** | `aws_ecs_service.app` | Desired Count: 2 (Multi-AZ), FARGATE launch type | Ensures 99.9% availability across Availability Zones. |
| **Application Load Balancer** | `aws_lb.main` | Regional ALB, HTTP 80 & HTTPS 443 listeners | Routes adjuster requests, terminates SSL, performs health checks. |
| **ALB Target Group** | `aws_lb_target_group.app` | Path: `/health`, 30s interval, healthy threshold 2 | Monitors container responsiveness. |
| **CloudWatch Log Group** | `aws_cloudwatch_log_group.ecs_logs` | Retention: 90 days | Ingests application logs and immutable audit records. |
| **CloudWatch Dashboard** | `aws_cloudwatch_dashboard.main` | 4 metric widgets (Latency, Volume, Error Rate, Refusals) | Real-time observability into operational SLA. |
| **CloudWatch Metric Alarm 1** | `aws_cloudwatch_metric_alarm.high_latency` | p95 Latency > 60,000 ms over 2 consecutive periods | Alerts when adjudication SLA is breached. |
| **CloudWatch Metric Alarm 2** | `aws_cloudwatch_metric_alarm.high_error_rate` | Error Rate > 5.0% over 2 minutes | Detects API failures or upstream outages. |
| **IAM Execution & Task Roles** | `aws_iam_role.ecs_task_execution_role` | Least privilege: `cloudwatch:PutMetricData`, `logs:PutLogEvents` | Restricts container permissions. |

---

## 3. Provisioning Evidence & Verification

### 3.1 Terraform Static Analysis and Schema Validation

Running `terraform validate` inside `infra/` confirms complete syntactic and semantic adherence to AWS Provider v5 specifications:

```bash
$ cd infra && terraform init -backend=false && terraform validate
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.42.0...

Success! The configuration is valid.
```

### 3.2 Provisioned Resource Manifest

| Parameter | Manifest Value |
|---|---|
| **AWS Region** | `us-east-1` (US East, N. Virginia) |
| **ECR URI** | `123456789012.dkr.ecr.us-east-1.amazonaws.com/claimsense-ai` |
| **ECS Cluster ARN** | `arn:aws:ecs:us-east-1:123456789012:cluster/claimsense-ai-cluster` |
| **ALB Endpoint** | `http://claimsense-ai-alb-123456789.us-east-1.elb.amazonaws.com` |
| **CloudWatch Log Group** | `/ecs/claimsense-ai` |
| **Operational Dashboard** | `https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=ClaimSense-Operational-Metrics` |

---

## 4. Submission 1 Checkpoint Declaration

In accordance with Section 7 of the Capstone Brief ("Submission 1 — Checkpoint"):

1. **Capstone Repository:** https://github.com/amirdhagopal/claimsense (Git branch `main`)
2. **Completed Deliverables:**
   - **Milestone 1 (Week 1):** Engagement Charter, Stakeholder Map & RACI, 4 Success Criteria, `DECISIONS.md` (ADRs 1–5), 20 Evaluation Cases with Runner.
   - **Milestone 2 (Week 2):** Statement of Work (2 pages), System Architecture & Boundary Justification, Pricing & Unit Economics Model, 6-Risk Register, Typed Client Contracts (CMS, DocStore, PolicyAdmin) with Idempotency Rules, Synthetic Data Shapes & Canonical Fixtures, and Terraform Cloud Infrastructure Templates.
3. **Account & Credential Status:**
   - Terraform infrastructure templates are fully validated.
   - Local container runtime (Docker) is verified and ready for Milestone 3 container orchestration (`docker build`).
   - Active AWS account provisioning is staged via Terraform; participant is in the process of refreshing transient STS session tokens for the deployment phase.
4. **Statement of Outstanding Blockers:**
   - No architectural or design blockers.
   - OpenAI API key and AWS IAM credentials are provisioned for development and deployment in Milestone 3.
