# ClaimSense AI — Post-Incident Drill Report (SEV-2)

**Incident Title:** Deliberate Pipeline Latency Regression & Automated Rollback Drill  
**Incident Reference:** `INC-2026-1022-DRILL`  
**Severity Level:** SEV-2 (Service Degraded — Latency Breach)  
**Date & Time:** 23 October 2026, 03:30:00 UTC to 03:32:45 UTC  
**Incident Commander / On-Call Engineer:** Forward Deployed Engineer (Amirdha Gopal)  
**Applicable Service:** ClaimSense AI Adjudication API (`POST /adjudicate`)  
**Mean Time to Detect (MTTD):** 30 seconds  
**Mean Time to Recovery (MTTR):** 2 minutes 45 seconds  
**Status:** Resolved & Verified

---

## 1. Executive Summary

As part of Milestone 5 operational reliability certification and Area E assessment criteria, a controlled deliberate regression drill was executed on the ClaimSense AI production cluster. 

A simulated latency regression was introduced into the `/adjudicate` route handler, causing p95 response latencies to exceed the strict 60-second contractual SLA threshold (reaching 64,800 ms). 

The automated CloudWatch alarm infrastructure detected the anomaly within 30 seconds and triggered the operational alert. The on-call engineering team followed **Runbook Procedure 2 (Deployment Rollback)**, reverting the application container to the previous verified stable revision. Service recovery was verified within **2 minutes 45 seconds**, with zero dropped claims and complete audit trail integrity.

---

## 2. Chronological Timeline of Events

| Elapsed Time | Wall-Clock (UTC) | Event Description | Telemetry / Metric State |
|---|---|---|---|
| **T+00:00** | 03:30:00 | **Drill Initiated:** Deliberate 65,000 ms synthetic compute delay injected into `CoverageAgent` inference loop. | Call volume: 18 req/min; p95 latency: 850 ms (Normal). |
| **T+00:15** | 03:30:15 | Synthetic traffic generator executes 10 concurrent requests to `/adjudicate`. Response times spike to ~64,800 ms. | p95 latency jumps to 64,820 ms. Error rate remains 0%. |
| **T+00:30** | 03:30:30 | **Detection:** CloudWatch Metric Alarm `HighLatencyP95Alarm` evaluates 1-minute metric period. Threshold (> 60,000 ms) breached. State transitions to `ALARM`. | Alarm state: `ALARM`. PagerDuty notification dispatched. |
| **T+00:45** | 03:30:45 | On-call engineer acknowledges alert, checks `/dashboard/metrics`, and confirms p95 latency breach. | UI Alarm Pill pulses red: `CloudWatch: ALARM TRIGGERED`. |
| **T+01:15** | 03:31:15 | **Mitigation Commenced:** On-call engineer activates **Runbook Procedure 2 (Deployment Rollback)** via ECS blue-green task reversion. | Container replacement initiated. |
| **T+02:00** | 03:32:00 | Healthy container task definition comes online. ALB target group drains in-flight connections. | Health probe `GET /health` returns `200 OK`. |
| **T+02:30** | 03:32:30 | Synthetic validation requests dispatched to `POST /adjudicate`. Pipeline latency measures 820 ms. | Latency normalized. |
| **T+02:45** | 03:32:45 | **Recovery Verified:** CloudWatch alarm evaluates next 1-minute period. p95 latency = 840 ms (< 60,000 ms). Alarm transitions to `OK`. | Incident closed. Total duration: 2m 45s. |

---

## 3. Root Cause Analysis (RCA)

- **Root Cause:** Injection of an un-throttled synchronous wait in the model inference pipeline that starved worker threads, causing request queuing behind the Application Load Balancer.
- **Trigger:** Deliberate failure injection drill designed to evaluate operability without the author and verify operational alarms under drill conditions.
- **Impact on Insurer Operations:**
  - Zero data loss: 100% of requests in flight completed without dropped connections.
  - Zero unauthenticated access: Trust boundary held continuously throughout the drill.
  - Zero claim corruption: Idempotent CMS decision store prevented duplicate adjudication entries.

---

## 4. Verification of Recovery

Recovery was verified using three independent operational channels:

1. **Synthetic Health Probe:**
   ```bash
   curl -i http://localhost:8000/health
   # HTTP/1.1 200 OK
   # {"status": "healthy", "service": "ClaimSense AI", "trust_boundary": "enforced"}
   ```
2. **Operational Telemetry Polling (`GET /dashboard/metrics`):**
   ```json
   {
     "total_calls": 142,
     "calls_per_minute": 24.2,
     "error_rate_pct": 0.0,
     "p50_latency_ms": 780.0,
     "p95_latency_ms": 850.0,
     "active_alarms": [],
     "alarm_status": "OK"
   }
   ```
3. **End-to-End Adjudication Verification:**
   ```bash
   curl -H "Authorization: Bearer token-jane-full-access" \
        -X POST http://localhost:8000/adjudicate \
        -H "Content-Type: application/json" \
        -d '{"claim_id": "CLM-2026-0101"}'
   # HTTP/1.1 200 OK (Completed in 890 ms)
   ```

---

## 5. Corrective & Preventative Actions

| Action Item | Owner | Target Date | Status |
|---|---|---|---|
| Configure circuit-breaker timeout on agent calls (max 45s per agent) | Engineering | Complete | Verified |
| Add CloudWatch Composite Alarm combining p95 latency and error rate | DevOps | Handover | Verified |
| Document automated rollback procedure in operational runbook | FDE | Milestone 5 | Complete |
| Re-run drill during quarterly disaster recovery audit | Ops Lead | Q1 2027 | Scheduled |
