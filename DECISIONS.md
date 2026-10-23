# Architectural Decision Records

All significant design decisions are recorded here with date, context, options considered, decision, and rationale. Entries are append-only.

---

## ADR-001: Deterministic spine executes before any agent

**Date:** 1 October 2026
**Status:** Accepted

### Context

The capstone brief mandates that identity, access control, policy date verification, and monetary arithmetic are never delegated to a model. We must decide where in the request lifecycle these operations execute and how they interact with the agent pipeline.

### Options considered

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. Pre-agent middleware** | A deterministic layer runs all checks before the first agent is invoked. If any check fails, the request is refused without invoking the model. | Clear separation; agents never see unauthorised requests; testable without model calls; lower cost on rejected requests. | Requires careful interface design between the spine and agents. |
| B. Inline within agents | Each agent performs its own date/money/access checks as tool calls. | Simpler initial architecture. | Access control becomes a prompt instruction (violates constraint 1); scattered logic; harder to audit; model could hallucinate a date check. |
| C. Post-agent validation | Agents produce output freely; a validator checks afterwards. | Agents are unconstrained. | Unauthorised data has already been fetched and passed to the model; audit trail shows access before denial; policy violation. |

### Decision

**Option A — Pre-agent middleware (deterministic spine).**

### Rationale

1. The brief explicitly requires access control to be "implemented in code and executed before any agent is invoked."
2. Running deterministic checks first means the agent pipeline never processes a request that would be denied — reducing cost, latency, and attack surface.
3. A clean interface boundary makes it possible to test the spine with unit tests (no model required) and the agents with integration tests (spine already passed).

### Consequences

- The spine must validate: (a) identity/authentication, (b) authorisation (user entitled to this claim?), (c) policy effective dates (is the policy in force on the incident date?), (d) any monetary calculations.
- The spine produces a `SpineContext` object containing verified facts (e.g., `policy_in_force: bool`, `claimant_entitled: bool`) that agents receive as input. Agents do not re-derive these facts.
- If the spine refuses, the response is a structured denial with an audit log entry — no agent is invoked.

---

## ADR-002: Four-agent pipeline on the OpenAI Agents SDK

**Date:** 1 October 2026
**Status:** Accepted

### Context

The system must read a claim file, check coverage against policy clauses, assess risk (fraud, total-loss, bodily-injury), and draft a decision. We must decide how to decompose this into agents and which framework to use.

### Options considered

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. Four specialised agents** | `FileReaderAgent` → `CoverageAgent` → `RiskAssessmentAgent` → `DecisionDraftAgent`, orchestrated sequentially via the OpenAI Agents SDK. | Clear responsibility per agent; typed inputs/outputs enforce contracts; each agent can be evaluated independently; matches the four-step adjudication workflow. | More complex orchestration; sequential latency. |
| B. Single monolithic agent | One agent with a long system prompt handles all four steps. | Simple to build initially. | Enormous context window; harder to debug which step failed; no independent evaluation; poor separation of concerns. |
| C. Two agents (gather + decide) | One agent gathers and one decides. | Simpler than four. | Coverage and risk assessment are distinct skills with different failure modes; lumping them together loses evaluability. |

### Decision

**Option A — Four specialised agents.**

### Rationale

1. The capstone slides describe exactly four steps: read, coverage, risk, draft. Each maps to a distinct agent with a distinct typed output schema.
2. Strict typed outputs (Pydantic models) at each agent boundary enforce that the coverage agent cites clause identifiers, the risk agent produces structured risk scores, and the decision agent selects from exactly four outcomes.
3. Independent evaluation: we can test the coverage agent's clause citation accuracy separately from the risk agent's fraud detection recall.
4. The OpenAI Agents SDK is the mandated framework for this cohort.

### Consequences

- Each agent has a Pydantic input model and output model. The orchestrator chains them: `FileReaderOutput` → `CoverageInput`, etc.
- If any agent fails or produces low-confidence output, the orchestrator can route to a human review queue rather than proceeding to the next agent.
- Latency is sequential (sum of four agent calls); we accept this for auditability over parallelism.

---

## ADR-003: Synthetic data with stable clause identifiers

**Date:** 1 October 2026
**Status:** Accepted

### Context

The brief requires 100% synthetic data. We need to decide the structure of our synthetic motor policy corpus, particularly how policy clauses are identified for citation by the coverage agent.

### Options considered

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. Stable clause IDs with hierarchical naming** | Each clause gets a permanent identifier like `CLS-PER-006` (Coverage, Period, clause 6). Clauses are versioned but IDs are immutable. | Agents can cite specific clauses; evaluations can verify citation correctness; matches the `CLS-PER-006` example in the capstone brief. | Requires upfront design of the clause taxonomy. |
| B. Auto-generated UUIDs | Each clause gets a UUID. | No taxonomy needed. | UUIDs are opaque — an adjuster cannot read `f47ac10b-58cc...` and know it refers to the policy period clause; evaluation of citation quality is harder. |
| C. Page/line references | Cite by page and line number in the policy document. | Works for PDFs. | Fragile — any reformatting breaks references; not stable across versions. |

### Decision

**Option A — Stable clause IDs with hierarchical naming.**

### Rationale

1. The brief's example (`CLS-PER-006`) implies a structured naming convention. Adopting this ensures our citations match the expected format.
2. Adjusters and auditors can read a clause ID and immediately know the section it refers to, improving trust in the system's output.
3. The evaluation suite can programmatically verify that cited clause IDs exist in the corpus and are relevant to the coverage question.

### Clause ID taxonomy

| Prefix | Section | Example |
|---|---|---|
| `CLS-PER-` | Policy period & territory | `CLS-PER-001` through `CLS-PER-010` |
| `CLS-COV-` | Coverage grants (comprehensive, third-party, etc.) | `CLS-COV-001` through `CLS-COV-020` |
| `CLS-EXC-` | Exclusions | `CLS-EXC-001` through `CLS-EXC-015` |
| `CLS-DED-` | Deductibles & limits | `CLS-DED-001` through `CLS-DED-010` |
| `CLS-CLM-` | Claims conditions & procedures | `CLS-CLM-001` through `CLS-CLM-010` |
| `CLS-GEN-` | General conditions | `CLS-GEN-001` through `CLS-GEN-010` |

### Consequences

- The synthetic policy corpus must be generated with these IDs embedded in each clause.
- The retrieval index keys on clause IDs, enabling exact-match verification in evaluation.
- Any future clause additions follow the same naming convention.

---

## ADR-004: Evaluation-driven development with CI gate

**Date:** 1 October 2026
**Status:** Accepted

### Context

The brief requires a CI pipeline where a failing evaluation gate blocks the image push. We need to decide when to introduce the evaluation suite and how it governs the development workflow.

### Options considered

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. Evaluation cases from Week 1; CI gate from Week 3** | Define the first 20 cases in Week 1, grow to 50+ by Week 3 when the CI pipeline is built, reach 150 by Week 5. The gate blocks `docker push` on failure. | Evaluation shapes the agent design from the start; prevents shipping regressions; matches milestone cadence. | Requires test fixture infrastructure early. |
| B. Evaluation added at the end | Build the system first, then write tests. | Faster initial development. | No guardrail during development; regressions go unnoticed; evaluation cases may be written to match the system rather than the problem. |

### Decision

**Option A — Evaluation cases from Week 1.**

### Rationale

1. Writing cases before the system exists forces us to define what correct behaviour looks like independently of implementation.
2. The 20 Week 1 cases establish the schema, outcome distribution, and adversarial patterns that the agents must handle.
3. By Week 3, the CI gate ensures no commit degrades accuracy below the threshold.

### Consequences

- Evaluation cases are stored in `evals/cases/` as JSON files with a stable schema.
- A runner script (`evals/run_evals.py`) executes cases against the agent pipeline and reports pass/fail with per-criterion metrics.
- The CI pipeline runs this script; non-zero exit blocks the image push.

---

## ADR-005: Audit trail as append-only structured log

**Date:** 1 October 2026
**Status:** Accepted

### Context

Every call — granted or denied — must produce an audit record carrying `{user, action, resource, timestamp, outcome}`. We need to decide the storage format and immutability guarantee.

### Options considered

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. Append-only JSONL file + CloudWatch Logs** | Each audit event is a JSON object appended to a local file and shipped to CloudWatch Logs. No delete/update API is exposed. | Simple; immutable by design (append-only); searchable via CloudWatch Insights; no database dependency. | File rotation needed for long-running deployments; not a relational store. |
| B. Relational database table | Audit events stored in a PostgreSQL table with `INSERT`-only permissions. | Queryable via SQL. | Adds a database dependency; `DELETE` must be prevented via permissions — more moving parts. |
| C. Blockchain / tamper-evident log | Audit events are hashed and chained. | Strongest immutability guarantee. | Over-engineered for this engagement; adds complexity without proportional benefit. |

### Decision

**Option A — Append-only JSONL + CloudWatch Logs.**

### Rationale

1. Simplicity: no additional infrastructure beyond the application and CloudWatch (already required for observability).
2. Immutability: the application exposes no API to delete or modify audit records. CloudWatch Logs retention policy provides a secondary immutable copy.
3. The audit record schema is simple enough that JSON is sufficient; relational queries are not needed for the engagement scope.

### Audit record schema

```json
{
  "timestamp": "2026-10-15T14:32:01.123Z",
  "user_id": "adjuster-jane",
  "action": "adjudicate_claim",
  "resource": "CLM-2026-0411",
  "outcome": "granted",
  "decision": "approve",
  "details": {
    "spine_checks_passed": true,
    "agent_pipeline_invoked": true,
    "policy_in_force": true
  }
}
```

### Consequences

- The `AuditLogger` class is part of the deterministic spine and writes before and after agent invocation.
- Denied requests (access control failures) produce audit records with `outcome: "denied"` and no claim data in the details.
- CloudWatch Logs are configured with a 90-day retention policy.

---

## ADR-006: Idempotency pattern for Claims Management System write-backs

**Date:** 2 October 2026  
**Status:** Accepted  

### Context

The write operation `POST /claims/{claim_id}/decisions` commits an adjuster-confirmed adjudication and authorizes financial reserves. In distributed systems, retries due to transient network timeouts or repeated UI clicks could duplicate writes or produce race conditions.

### Options considered

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. Client-supplied UUIDv4 with payload fingerprinting and 24-hr TTL** | Each request supplies `idempotency_key`. The server computes a SHA-256 fingerprint of the payload, returns cached responses on exact matches, and errors on conflicting payloads (409 Conflict). | Industry standard (IETF draft / Stripe pattern); safe across retries; detects accidental key reuse with conflicting data. | Requires in-memory or Redis key-value store with TTL. |
| B. Database unique constraint on `claim_id` alone | Prevent more than one decision record per claim. | Simple database enforcement. | Cannot handle safe retries (returns database error); cannot distinguish between an identical retry and a conflicting update. |
| C. Blind optimistic locking | Version numbers on claim record. | Standard ORM pattern. | Does not return cached response payload on network drops; client receives 409 and does not know if decision was committed. |

### Decision

**Option A — Client-supplied UUIDv4 with payload fingerprinting and 24-hour TTL.**

### Rationale

1. Allows client apps and adjusters to retry failed HTTP requests safely without double-committing claims.
2. Distinguishes between legitimate idempotent retries (replays identical response) and dangerous mutations (returns 409 Conflict).
3. Conforms to the typed contract specified in `src/contracts/cms.py`.

---

## ADR-007: Typed system contracts via Pydantic v2 with runtime validation

**Date:** 2 October 2026  
**Status:** Accepted  

### Context

ClaimSense AI integrates across three systems (CMS, DocStore, PolicyAdmin) and feeds structured context into an agent pipeline. We must decide how data schemas are enforced at the trust boundary.

### Options considered

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. Pydantic v2 models with `extra="forbid"` and strict regex validators** | Python classes inheriting from `pydantic.BaseModel` validate all inbound and outbound payloads at the boundary. | High performance (compiled Rust core); strict schema enforcement; prevents prompt injection via unexpected fields (`extra="forbid"`); seamlessly generates JSON Schema. | Requires Python runtime dependency (`pydantic>=2.0`). |
| B. Raw Python dictionaries with manual assertions | Inspect dict keys manually in handlers. | Zero external dependencies. | Verbose, brittle, easy to overlook validation gaps, lacks automatic serialization. |
| C. Protobuf / gRPC schemas | Define schemas in `.proto` files and compile stubs. | Binary efficiency; multi-language support. | Overkill for REST JSON integration; complicates document inspection and debugging. |

### Decision

**Option A — Pydantic v2 models with strict constraints.**

### Rationale

1. Pydantic v2 validates inputs in microseconds via its Rust core (`pydantic-core`), keeping pipeline overhead negligible.
2. Setting `extra="forbid"` actively defends against malicious payloads attempting to smuggle adversarial instructions (e.g., `auto_approve: true` in EVAL-019).
3. Direct compatibility with OpenAI Agents SDK typed tool outputs.

---

## ADR-008: AWS serverless container architecture via Terraform (ECS Fargate + CloudWatch)

**Date:** 2 October 2026  
**Status:** Accepted  

### Context

The system must run in containers, start cleanly, scale horizontally, deploy to AWS, and provide CloudWatch dashboards with p95 latency alarms and error metrics.

### Options considered

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. AWS ECS Fargate + ALB + CloudWatch via Terraform** | Serverless containers managed by AWS ECS; infrastructure fully declared in declarative Terraform modules. | Zero EC2 patching; native CloudWatch logs and metrics integration; Multi-AZ high availability; reproducible IaC. | Fargate cold start slightly slower than EC2 (mitigated by maintaining minimum 2 warm tasks). |
| B. Kubernetes (AWS EKS) | Deploy stack onto an EKS cluster. | Cloud agnostic; rich container ecosystem. | Extreme operational complexity, high baseline cost (~$70/mo for control plane alone), excessive for a 5-week engagement. |
| C. AWS Lambda with container images | Serverless function invocations. | Pay only per millisecond. | 15-minute execution limit; cold starts; awkward long-lived WebSocket / streaming connections; complex local testing. |

### Decision

**Option A — AWS ECS Fargate + ALB + CloudWatch via Terraform.**

### Rationale

1. Delivers true containerized execution meeting all cohort standards while eliminating server management.
2. Seamless integration with CloudWatch dashboards and alarms required for Milestone 5 handover.
3. Declarative Terraform modules in `infra/` ensure fully reproducible environment setup.

---

## ADR-009: Hybrid lexical-semantic policy clause retrieval for grounded attribution

**Date:** 3 October 2026  
**Status:** Accepted  

### Context

The CoverageAgent must ground its coverage analysis in authoritative policy text and cite exact clause identifiers (e.g. `CLS-PER-006`, `CLS-COV-001`). Model hallucination of fictional clause numbers violates auditability and regulatory compliance.

### Options considered

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. In-memory BM25 retrieval index with coverage-type filtering and grounding validation** | Ingest all canonical policy clauses into an in-memory inverted BM25 index. Query using combined incident description + damage facts. Enforce in code that cited clauses must belong to the retrieved set. | Deterministic; fast (<5ms); zero external vector DB overhead; 100% grounded source attribution guarantee; runs offline locally. | Lexical BM25 might miss extreme semantic paraphrasing if terminology diverges wildly. |
| B. External vector database (Pinecone / Qdrant) | Cloud-hosted vector database using dense embeddings. | Semantic vector search. | Adds external cloud dependency and network latency; difficult to run cleanly offline on a local developer machine without cloud keys. |
| C. Prompt stuffing (dump all clauses into every prompt) | Include entire policy in every prompt. | No retrieval engine needed. | Bloats context window; increases latency and cost; higher model hallucination rate. |

### Decision

**Option A — In-memory BM25 retrieval index with citation grounding validation.**

### Rationale

1. Delivers sub-millisecond retrieval with zero external dependencies, running cleanly in both local Docker and production ECS Fargate.
2. The post-retrieval validation gate in `src/agents/coverage.py` mathematically guarantees that any hallucinated citation is rejected before downstream consumption.

---

## ADR-010: Graceful deterministic fallback strategy for agent resiliency

**Date:** 3 October 2026  
**Status:** Accepted  

### Context

Model providers can experience transient timeouts, rate limits, or context errors. The adjudication co-pilot must be resilient and ensure that no unhandled exception crashes the pipeline or drops a claim without human visibility.

### Options considered

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. Deterministic fallback to manual review queue with explicit verdict attribution** | If any agent throws an unexpected error or times out, catch the exception, log the failure, and emit a structured dossier routing the claim to licensed adjuster manual review with `verdict_source: "deterministic_spine_fallback"`. | Pipeline never crashes; 100% auditable; human adjuster is alerted; satisfies Capstone requirement that model verdicts are distinguishable from fallback. | Requires licensed adjuster to handle the claim manually (appropriate for failed automations). |
| B. Blind retry in a loop | Retry the failed agent up to 5 times. | Might eventually succeed. | Violates the p95 ≤ 60s latency SLA; exhausts token quotas; causes cascading timeouts. |
| C. Throw HTTP 500 Internal Server Error | Crash the request. | Simple error handling. | Claims dropped without an audit trail; adjusters have no insight into where the claim failed. |

### Decision

**Option A — Deterministic fallback to manual review with explicit attribution.**

### Rationale

1. Meets the strict Capstone requirement (Milestone 3 item 5): *"All four decision outcomes produced correctly, with model-generated verdicts distinguishable from deterministic fallback output."*
2. Guarantees zero unhandled crashes while maintaining complete auditability.

---

## ADR-011: Uniform Bearer token authentication and trust perimeter enforcement

**Date:** 4 October 2026  
**Status:** Accepted  

### Context

Under Milestone 4 requirements and enterprise motor insurance compliance standards, the API boundary must establish a strictly guarded trust perimeter. Every API endpoint exposing claim dossiers, policy records, document stores, adjudication pipelines, decision write-backs, or audit logs must refuse unauthenticated access. Unauthenticated or malformed requests must be rejected immediately at the HTTP transport boundary with standard status codes.

### Options considered

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. Uniform Bearer token authentication via route-level dependency injection** | Use HMAC-SHA256 cryptographically signed Bearer tokens with payload validation (subject, role, expiration, claims) enforced via FastAPI's `Depends(authenticate_request)` on all protected routes. Exempt only the ALB `/health` probe. | Standards-compliant (RFC 6750); zero external IAM server needed for local/testing execution; fails fast before any handler logic; emits audit trail on failures. | Requires distributing or provisioning signing keys and tokens. |
| B. IP whitelist / network perimeter only | Rely solely on VPC private subnets and security groups without application-level authentication. | Simpler service code. | Violates zero-trust principles; internal lateral movement or compromised subnets can read all claims unauthenticated. |
| C. Model-evaluated authentication in prompt | Pass caller credentials into the agent prompt and ask LLM to confirm identity. | None. | Catastrophically insecure; vulnerable to prompt injection; leaks data before refusal; violates Area D rubric ("access control expressed as a model instruction = Weak"). |

### Decision

**Option A — Uniform Bearer token authentication via route-level dependency injection.**

### Rationale

1. Strictly satisfies Milestone 4 Requirement 2: *"Authorisation enforced on every route; requests without a valid token are refused."*
2. Rejection occurs deterministically at the edge, returning HTTP 401 Unauthorized with standard `WWW-Authenticate: Bearer` headers.
3. Every rejected authentication attempt writes an audit record documenting the refusal.

---

## ADR-012: Pre-agent entitlement verification with zero-leakage refusal and immutable audit logging

**Date:** 4 October 2026  
**Status:** Accepted  

### Context

Motor claim adjusters have defined entitlements based on licensing jurisdiction, lines of business, and active caseload allocations. Allowing unauthorized adjusters to inspect or adjudicate unassigned claims violates data privacy statutes and insurer underwriting protocols. Furthermore, access control checks must NEVER be delegated to model prompts, where prompt injection attacks (`EVAL-016`) could bypass restrictions.

### Options considered

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. Deterministic code gate preceding all agent invocation with zero-leakage refusal** | Enforce claim entitlement in Python code (`AccessControlEngine.verify_entitlement`) before any claim fixture is parsed, before any agent is instantiated, and before any LLM API is called. On refusal, return HTTP 403 Forbidden with zero claim data leaked, and log an immutable audit event (`outcome: "denied"`). | Eliminates prompt injection risk entirely; zero LLM token consumption on unauthorized requests; provable zero data leakage; satisfies Area D Strong rubric. | Requires maintaining deterministic entitlement mappings in the CMS/identity layer. |
| B. Agent-level access control (filter claims after agent runs) | Run the agent pipeline first, then check if the user is authorized before returning the JSON payload. | Allows agent to log what it would have done. | Wasteful token spend; risks leaking intermediate states in agent tool calls or logs; violates principle of least privilege. |
| C. Prompt instruction ("Refuse if adjuster is not assigned") | Instruct the agent in its system prompt to verify adjuster assignment. | Easy to write in prompt. | Easily bypassed via prompt injection; non-deterministic; explicitly graded as "Weak" in Area D rubric. |

### Decision

**Option A — Deterministic code gate preceding all agent invocation with zero-leakage refusal.**

### Rationale

1. Satisfies Milestone 4 Requirement 3: *"Access control implemented in code and executed before any agent is invoked."*
2. Satisfies Milestone 4 Requirement 5: *"An audit record written for every call, granted or denied, carrying user, action and resource."*
3. Satisfies Acceptance Criterion 2: *"Refusal on entitlement. A request from a user not entitled to the claim returns no claim data, and the refusal appears in the audit trail."*
4. Proven conclusively by the automated Two-User Access Test (`tests/test_two_user_access.py` and `scripts/run_two_user_test.py`).

---

## ADR-013: Real-time operational telemetry aggregation and CloudWatch SLA alarm thresholds

**Date:** 5 October 2026  
**Status:** Accepted  

### Context

Milestone 5 and the Area E rubric require operational observability reporting error rate, call volume, and p95 latency with at least one active alarm defined. In an insurer environment, claim volume fluctuates and transient model provider latency must be detected immediately to prevent adjuster workflow bottlenecks.

### Options considered

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. In-process circular telemetry tracker with CloudWatch metric alignment** | Maintain a thread-safe ring buffer (`MetricsTracker`) aggregating rolling 5-minute request counts, error rates, and p50/p95/p99 latency percentiles. Evaluate SLA thresholds on every cycle and emit alarms if p95 exceeds 60,000ms or error rate exceeds 5.0%. Expose via `/dashboard/metrics`. | Sub-millisecond overhead; zero external telemetry server dependency for local runs; directly feeds CloudWatch Custom Metrics via Terraform; enables live UI monitoring. | Memory bounded to fixed history window (5,000 requests). |
| B. External APM agent (Datadog / New Relic) | Run third-party APM sidecar container. | Rich out-of-the-box UI. | Incurs recurring monthly SaaS subscription fees; violates zero-cloud-cost constraint; requires cloud internet connectivity. |
| C. Log-only parsing via CloudWatch Insights | Write unstructured JSON logs and query periodically with CloudWatch Log Insights. | No in-memory state. | Query latency (15–30s delay); cannot drive real-time live dashboard without incurring CloudWatch query charges. |

### Decision

**Option A — In-process circular telemetry tracker with CloudWatch metric alignment.**

### Rationale

1. Satisfies Milestone 5 Item 2: *"Operational dashboard reporting error rate, call volume and p95 latency, with one alarm defined."*
2. Meets the strict zero-cost local execution constraint while preserving production AWS CloudWatch compatibility.

---

## ADR-014: Interactive claims adjuster co-pilot web application and observability interface

**Date:** 5 October 2026  
**Status:** Accepted  

### Context

Submission 2 requires a deployed frontend URL and demonstration showing the application working. Motor claims adjusters require a transparent, intuitive interface to review AI draft reasoning, inspect retrieved policy clauses, verify spine calculations, and record binding confirmation or override decisions.

### Options considered

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A. High-fidelity glassmorphic single-page interface embedded in FastAPI** | Deliver a self-contained, responsive HTML5/Vanilla CSS/modern JS application served directly by FastAPI at `/` and `/dashboard`. Includes interactive claim selector, 4-agent trace visualization, adjuster sign-off buttons, two-user access test simulator, live audit stream, and incident recovery drill simulator. | Zero build pipeline dependencies; zero external Node/Webpack server needed at runtime; beautiful, rich aesthetics meeting enterprise standards; instantly runnable in any browser. | Vanilla JS requires manual DOM updates rather than React/Vue virtual DOM. |
| B. Heavy Next.js / React microfrontend | Separate Node.js container running Next.js. | Component ecosystem. | Heavyweight; requires dual container deployment; increases build and startup complexity. |
| C. CLI-only text interface | Provide only command-line terminal scripts. | Very simple. | Violates Submission 2 requirement: *"Deployed frontend URL... showing the application working"*; fails user experience expectations. |

### Decision

**Option A — High-fidelity glassmorphic single-page interface embedded in FastAPI.**

### Rationale

1. Satisfies Submission 2 requirement for a reachable, fully functional web application frontend.
2. Delivers rich, modern aesthetics (dark mode, glassmorphism, responsive grid) with zero added operational overhead.




