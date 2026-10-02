# ClaimSense AI — Stakeholder Map & RACI Matrix

**Version:** 1.0
**Date:** 1 October 2026

---

## 1. Stakeholder Map

### 1.1 Stakeholder Identification

| Stakeholder | Role in engagement | Organisation | Influence | Interest |
|---|---|---|---|---|
| **Head of Claims Operations** | Executive sponsor; approves go-live and budget. | Apex Motor Insurance | High | High |
| **Claims Team Lead** | Day-to-day reviewer of co-pilot output; validates decisions against adjuster judgment. | Apex Motor Insurance | High | High |
| **Licensed Adjusters (×38)** | Daily users of ClaimSense; confirm every co-pilot recommendation before it becomes a decision. | Apex Motor Insurance | Medium | High |
| **IT Security Officer** | Approves the trust boundary design; can block rollout if access controls are insufficient. | Apex Motor Insurance | High | Medium |
| **Compliance / Regulatory Lead** | Validates audit trail completeness and regulatory alignment; can block rollout. | Apex Motor Insurance | High | Medium |
| **CMS System Owner** | Owns the Claims Management System; approves API integration contracts. | Apex Motor Insurance (IT) | Medium | Medium |
| **DocStore System Owner** | Owns the Document Store; approves document retrieval integration. | Apex Motor Insurance (IT) | Medium | Low |
| **PolicyAdmin System Owner** | Owns Policy Administration; approves policy data access and clause retrieval. | Apex Motor Insurance (IT) | Medium | Medium |
| **Forward Deployed Engineer (FDE)** | Engagement lead; designs, builds, and delivers ClaimSense AI. | Consulting (IK) | High | High |

### 1.2 Stakeholder Influence–Interest Grid

```
                    High Interest
                         │
     ┌───────────────────┼───────────────────┐
     │  KEEP SATISFIED   │  MANAGE CLOSELY   │
     │                   │                   │
     │  • IT Security    │  • Head of Claims │
High │    Officer        │    Operations     │
Infl │  • Compliance     │  • Claims Team    │
     │    Lead           │    Lead           │
     │                   │  • FDE            │
     ├───────────────────┼───────────────────┤
     │  MONITOR          │  KEEP INFORMED    │
     │                   │                   │
Low  │  • DocStore Owner │  • Licensed       │
Infl │                   │    Adjusters      │
     │                   │  • CMS Owner      │
     │                   │  • PolicyAdmin    │
     │                   │    Owner          │
     └───────────────────┼───────────────────┘
                    Low Interest
```

---

## 2. RACI Matrix

**R** = Responsible (does the work)
**A** = Accountable (approves / owns the outcome)
**C** = Consulted (provides input before)
**I** = Informed (notified after)

### 2.1 Engagement-Level RACI

| Activity | Head of Claims Ops | Claims Team Lead | Licensed Adjusters | IT Security | Compliance | System Owners (CMS/Doc/Policy) | FDE |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Engagement charter sign-off** | **A** | C | I | I | I | I | **R** |
| **Success criteria definition** | **A** | **R** | C | I | C | I | **R** |
| **Architecture & design** | I | C | I | C | I | C | **R/A** |
| **Trust boundary design** | I | I | I | **A** | C | C | **R** |
| **Audit trail requirements** | I | C | I | C | **A** | I | **R** |
| **API contract definition** | I | I | I | I | I | **A** | **R** |
| **Agent pipeline build** | I | I | I | I | I | I | **R/A** |
| **Evaluation suite design** | I | C | C | I | C | I | **R/A** |
| **UAT / co-pilot output review** | I | **A** | **R** | I | I | I | **R** |
| **Go-live approval** | **A** | C | I | C | C | C | **R** |
| **Incident response & runbook** | I | C | I | C | I | I | **R/A** |

### 2.2 Per-Claim Decision RACI (Runtime)

This RACI applies to every claim processed through ClaimSense in production:

| Step | ClaimSense (Deterministic Spine) | ClaimSense (Agent Pipeline) | Licensed Adjuster | Claims Team Lead |
|---|:---:|:---:|:---:|:---:|
| **Identity verification** | **R/A** | — | — | I |
| **Access control check** | **R/A** | — | — | I |
| **Policy date verification** | **R/A** | — | — | — |
| **Monetary arithmetic** | **R/A** | — | — | — |
| **File reading & comprehension** | — | **R** | I | I |
| **Coverage determination** | — | **R** | C | I |
| **Risk assessment (fraud/TL/BI)** | — | **R** | C | I |
| **Decision draft** | — | **R** | I | I |
| **Decision confirmation** | — | — | **R/A** | I |
| **Audit log entry** | **R/A** | — | — | I |

### 2.3 Key Observations

1. **The Licensed Adjuster is the sole decision-maker.** ClaimSense drafts; the adjuster confirms. The system never auto-decides.
2. **IT Security Officer can block rollout** if the trust boundary does not satisfy their requirements — this makes security design a Week 1 consultation priority.
3. **Compliance Lead can block rollout** if the audit trail is incomplete — audit record schema must be agreed by end of Week 2.
4. **The FDE is responsible for all technical deliverables** and accountable for the architecture, but the Head of Claims Operations is accountable for the engagement outcome.

---

## 3. Communication Plan

| Cadence | Audience | Format | Purpose |
|---|---|---|---|
| Daily (async) | Claims Team Lead | Slack/email update | Progress, blockers |
| Weekly (sync) | Head of Claims Ops, Claims Team Lead, IT Security | 30-min standup | Milestone review, decision escalation |
| Ad hoc | System Owners | Direct message | API contract clarification |
| End of Week 2 | All stakeholders | Checkpoint submission | Confirm readiness for build phase |
| End of Week 5 | All stakeholders | Presentation + demo | Final handover |
