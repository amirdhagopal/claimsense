# ClaimSense AI — Success Criteria

**Version:** 1.0
**Date:** 1 October 2026

---

## Overview

Four quantified success criteria govern the engagement. Each criterion has a baseline (current state), a target (engagement exit), a measurement method, and a minimum threshold below which the engagement would be considered unsuccessful.

These criteria are designed to be **measurable on the evaluation suite** — they can settle a later dispute about whether the engagement worked.

---

## Criterion 1: Decision Accuracy

> *Does ClaimSense recommend the correct decision outcome?*

| Attribute | Value |
|---|---|
| **Metric** | Percentage of evaluation cases where the co-pilot's recommended decision matches the ground-truth label. |
| **Baseline** | N/A (no automated system today; adjuster-to-adjuster agreement estimated at ~78%). |
| **Target** | **≥ 90%** agreement with ground-truth across all four decision outcomes (approve, flag, route, deny). |
| **Minimum threshold** | ≥ 80%. Below this, the co-pilot creates more review work than it saves. |
| **Measurement** | Automated evaluation suite run on CI. Each case has a `ground_truth_decision` field; the agent's `recommended_decision` is compared. Accuracy = correct / total. |
| **Breakdown required** | Per-outcome accuracy reported separately (approve, flag, route, deny) to detect systematic bias toward any single outcome. |

---

## Criterion 2: Pipeline Latency (Time-to-First-Decision)

> *How long does it take from claim submission to a draft decision being available?*

| Attribute | Value |
|---|---|
| **Metric** | Wall-clock time from API request receipt to draft decision response, measured at p50 and p95. |
| **Baseline** | 47 minutes (manual adjuster process). |
| **Target** | **p50 ≤ 30 seconds, p95 ≤ 60 seconds.** |
| **Minimum threshold** | p95 ≤ 120 seconds. Beyond this, adjusters will not trust the system to be faster than manual. |
| **Measurement** | Instrumented in the API layer. Every `/adjudicate` request logs `request_received_at` and `response_sent_at`. Latency = delta. Aggregated in CloudWatch metrics. |
| **Exclusions** | Network transit time between the adjuster's browser and the service is excluded; only server-side processing time is measured. |

---

## Criterion 3: Adjuster Confirmation Rate

> *How often does the licensed adjuster accept the co-pilot's recommendation without modification?*

| Attribute | Value |
|---|---|
| **Metric** | Percentage of decisions where the adjuster confirms the co-pilot's recommendation as-is (no override, no edit to reasoning). |
| **Baseline** | N/A (no co-pilot today). Industry benchmark for decision-support acceptance in similar tools: 60–70%. |
| **Target** | **≥ 75%** confirmation rate on production-like evaluation claims. |
| **Minimum threshold** | ≥ 60%. Below this, the co-pilot is adding friction rather than accelerating the workflow. |
| **Measurement** | Simulated in the evaluation suite via adjuster-role review. Each case records `adjuster_action ∈ {confirm, override, escalate}`. Confirmation rate = confirm / total. In production, measured via the decision write-back API (`POST /claims/{id}/decisions`) which records whether the confirmed decision matches the draft. |
| **Note** | This criterion is partially evaluated via synthetic adjuster review during the engagement; full measurement requires production deployment. The evaluation suite provides a lower-bound estimate. |

---

## Criterion 4: Fraud Routing Accuracy

> *Does ClaimSense correctly flag claims that should be referred for fraud investigation?*

| Attribute | Value |
|---|---|
| **Metric** | Precision and recall of the "Flag/Refer" decision outcome on claims with known fraud indicators. |
| **Baseline** | Current rule-based score threshold has ~45% precision (many false positives) and ~60% recall (misses narrative-based fraud). |
| **Target** | **Precision ≥ 80%, Recall ≥ 85%** on the evaluation suite's fraud-labelled cases. |
| **Minimum threshold** | Precision ≥ 65%, Recall ≥ 70%. Below this, the system performs no better than the existing score threshold. |
| **Measurement** | The evaluation suite includes cases with `fraud_ground_truth ∈ {true, false}`. For cases where `fraud_ground_truth = true`, the agent should produce `recommended_decision = flag`. Precision = true flags / all flags. Recall = true flags / all actual fraud cases. |
| **Adversarial test** | The suite includes cases designed to bypass fraud detection: contradictory medical notes, suspicious timing with clean metadata, and staged losses. These count toward recall. |

---

## Summary Table

| # | Criterion | Metric | Target | Minimum |
|---|---|---|---|---|
| 1 | Decision Accuracy | % correct across 4 outcomes | ≥ 90% | ≥ 80% |
| 2 | Pipeline Latency | p50 / p95 wall-clock time | ≤ 30s / ≤ 60s | — / ≤ 120s |
| 3 | Adjuster Confirmation | % confirmed as-is | ≥ 75% | ≥ 60% |
| 4 | Fraud Routing Accuracy | Precision / Recall on fraud cases | ≥ 80% / ≥ 85% | ≥ 65% / ≥ 70% |

---

## Evaluation Cadence

| Milestone | Cases | Purpose |
|---|---|---|
| Week 1 (M1) | 20 cases | Baseline; validates schema and outcome distribution. |
| Week 3 (M3) | 50+ cases | CI gate; validates agent pipeline correctness. |
| Week 5 (M5) | 150 cases | Final; includes adversarial families. All four criteria measured. |
