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
