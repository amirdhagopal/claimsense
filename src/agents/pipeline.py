"""
ClaimSense AI — End-to-End Adjudication Pipeline

Orchestrates the deterministic spine and the four-agent adjudication pipeline
(FileReader -> Coverage -> RiskAssessment -> DecisionDraft).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional
from src.agents.coverage import CoverageAgent
from src.agents.decision_drafter import DecisionDraftAgent
from src.agents.file_reader import FileReaderAgent
from src.agents.risk_assessment import RiskAssessmentAgent
from src.agents.schemas import (
    DraftDecisionOutput,
    FileReaderOutput,
    CoverageOutput,
    RiskOutput,
)
from src.contracts.cms import ClaimRecord, DecisionOutcome, DecisionDetail
from src.contracts.docstore import DocumentContentResponse
from src.contracts.policyadmin import PolicyRecord
from src.retrieval.policy_index import PolicyClauseIndex
from src.spine.access_control import UserIdentity
from src.spine.audit_logger import AuditLogger
from src.spine.context import SpineContext
from src.spine.orchestrator import DeterministicSpine, AccessDeniedException

logger = logging.getLogger(__name__)


class AdjudicationDossier:
    """
    Complete dossier containing intermediate outputs, the final decision,
    and per-agent execution lineage / token telemetry.
    """
    def __init__(
        self,
        spine_context: SpineContext,
        file_reader_output: Optional[FileReaderOutput],
        coverage_output: Optional[CoverageOutput],
        risk_output: Optional[RiskOutput],
        draft_decision: DraftDecisionOutput,
        telemetry: Optional[dict[str, Any]] = None,
    ):
        self.spine_context = spine_context
        self.file_reader_output = file_reader_output
        self.coverage_output = coverage_output
        self.risk_output = risk_output
        self.draft_decision = draft_decision
        self.telemetry = telemetry or {}


class AdjudicationPipeline:
    """
    The main ClaimSense AI adjudication orchestrator.
    """

    def __init__(
        self,
        clause_index: Optional[PolicyClauseIndex] = None,
        model_name: Optional[str] = None,
    ):
        self.clause_index = clause_index or PolicyClauseIndex()
        self.file_reader_agent = FileReaderAgent(model_name=model_name)
        self.coverage_agent = CoverageAgent(model_name=model_name)
        self.risk_agent = RiskAssessmentAgent(model_name=model_name)
        self.decision_draft_agent = DecisionDraftAgent(model_name=model_name)

    def adjudicate(
        self,
        user: UserIdentity,
        claim: ClaimRecord,
        policy: PolicyRecord,
        documents: list[DocumentContentResponse],
    ) -> AdjudicationDossier:
        """
        Executes the full adjudication workflow:
        1. Deterministic Spine checks (access control, dates, money)
        2. Agent 1: FileReaderAgent
        3. Agent 2: CoverageAgent (RAG retrieval)
        4. Agent 3: RiskAssessmentAgent
        5. Agent 4: DecisionDraftAgent
        6. Audit Logging
        """
        # Step 1: Deterministic Spine (Throws AccessDeniedException if not entitled)
        pipeline_t0 = time.perf_counter()
        spine_t0 = time.perf_counter()
        spine_context = DeterministicSpine.execute_pre_agent_checks(user, claim, policy)
        spine_ms = round((time.perf_counter() - spine_t0) * 1000.0, 2)

        spine_span = {
            "step": "1. DeterministicSpine",
            "type": "deterministic_code",
            "status": "rejected" if spine_context.spine_must_reject else "passed",
            "latency_ms": spine_ms,
            "input_lineage": f"Claim ({claim.claim_id}) + Policy ({policy.policy_id}) + Identity ({user.user_id})",
            "output_lineage": (
                f"SpineContext(in_force={spine_context.policy_in_force}, "
                f"vin_scheduled={spine_context.vehicle_scheduled}, "
                f"ratio={spine_context.repair_to_value_ratio:.1%}, "
                f"max_payout=${spine_context.max_authorized_payout:,.2f})"
            ),
            "prompt_tokens": 0,
            "system_tokens": 0,
            "schema_tokens": 0,
            "context_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

        # Short-circuit if deterministic spine mandates immediate rejection (lapsed policy / unscheduled VIN)
        if spine_context.spine_must_reject:
            rejection_clause = "CLS-PER-001" if not spine_context.policy_in_force else "CLS-COV-008"
            detail = DecisionDetail.POLICY_LAPSED if not spine_context.policy_in_force else DecisionDetail.VEHICLE_NOT_SCHEDULED
            draft_decision = DraftDecisionOutput(
                claim_id=claim.claim_id,
                decision=DecisionOutcome.DENY,
                decision_detail=detail,
                reasoning=f"Claim rejected deterministically: {spine_context.rejection_reason} Grounded in policy clause {rejection_clause} (effective {policy.effective_date} to expiry {policy.expiry_date}).",
                cited_clauses=[rejection_clause],
                payout_authorized=0.0,
                verdict_source="deterministic_spine",
                requires_licensed_adjuster_confirmation=True,
            )
            AuditLogger.log(
                user_id=user.user_id,
                action="adjudicate_claim",
                resource=claim.claim_id,
                outcome="granted",
                decision=draft_decision.decision.value,
                details={
                    "decision_detail": draft_decision.decision_detail.value if draft_decision.decision_detail else None,
                    "verdict_source": draft_decision.verdict_source,
                    "cited_clauses": draft_decision.cited_clauses,
                    "policy_in_force": spine_context.policy_in_force,
                    "payout_authorized": draft_decision.payout_authorized,
                },
            )
            skipped_spans = [
                {
                    "step": name,
                    "type": "llm_agent",
                    "status": "skipped (spine short-circuit)",
                    "latency_ms": 0.0,
                    "input_lineage": "Short-circuited by Deterministic Spine",
                    "output_lineage": "0 LLM calls invoked",
                    "prompt_tokens": 0,
                    "system_tokens": 0,
                    "schema_tokens": 0,
                    "context_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                }
                for name in [
                    "2. Agent 1: FileReaderAgent",
                    "3. Agent 2: CoverageAgent (BM25 RAG)",
                    "4. Agent 3: RiskAssessmentAgent",
                    "5. Agent 4: DecisionDraftAgent",
                ]
            ]
            telemetry = {
                "claim_id": claim.claim_id,
                "decision": draft_decision.decision.value,
                "verdict_source": draft_decision.verdict_source,
                "total_latency_ms": round((time.perf_counter() - pipeline_t0) * 1000.0, 1),
                "total_prompt_tokens": 0,
                "total_system_tokens": 0,
                "total_schema_tokens": 0,
                "total_context_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "spans": [spine_span] + skipped_spans,
            }
            return AdjudicationDossier(
                spine_context=spine_context,
                file_reader_output=None,
                coverage_output=None,
                risk_output=None,
                draft_decision=draft_decision,
                telemetry=telemetry,
            )

        try:
            # Step 2: FileReaderAgent
            file_reader_output = self.file_reader_agent.process(
                claim=claim,
                documents=documents,
                spine_context=spine_context,
            )
            fr_tel = dict(self.file_reader_agent.last_call_telemetry)

            # Step 3: CoverageAgent
            coverage_output = self.coverage_agent.process(
                claim=claim,
                policy=policy,
                file_reader_output=file_reader_output,
                spine_context=spine_context,
                clause_index=self.clause_index,
            )
            cov_tel = dict(self.coverage_agent.last_call_telemetry)

            # Step 4: RiskAssessmentAgent
            risk_output = self.risk_agent.process(
                claim=claim,
                documents=documents,
                file_reader_output=file_reader_output,
                coverage_output=coverage_output,
                spine_context=spine_context,
            )
            risk_tel = dict(self.risk_agent.last_call_telemetry)

            # Step 5: DecisionDraftAgent
            draft_decision = self.decision_draft_agent.process(
                claim=claim,
                policy=policy,
                file_reader_output=file_reader_output,
                coverage_output=coverage_output,
                risk_output=risk_output,
                spine_context=spine_context,
            )
            dd_tel = dict(self.decision_draft_agent.last_call_telemetry)

            doc_ids = ", ".join(d.doc_id for d in documents) or "none"
            agent_spans = [
                {
                    "step": "2. Agent 1: FileReaderAgent",
                    "type": "llm_agent",
                    "status": "completed",
                    "input_lineage": f"Claim Narrative + {len(documents)} DocStore Docs [{doc_ids}]",
                    "output_lineage": (
                        f"FileReaderOutput(damage={file_reader_output.damage_locations}, "
                        f"contradictions={len(file_reader_output.identified_contradictions)}, "
                        f"injuries={file_reader_output.injuries_reported})"
                    ),
                    **fr_tel,
                },
                {
                    "step": "3. Agent 2: CoverageAgent (BM25 RAG)",
                    "type": "llm_agent",
                    "status": "completed",
                    "input_lineage": f"FileReaderOutput + Policy ({policy.policy_id}) + Top-6 BM25 Clauses",
                    "output_lineage": (
                        f"CoverageOutput(applies={coverage_output.coverage_applies}, "
                        f"cited={coverage_output.cited_clause_ids}, "
                        f"exclusions={coverage_output.exclusions_triggered})"
                    ),
                    **cov_tel,
                },
                {
                    "step": "4. Agent 3: RiskAssessmentAgent",
                    "type": "llm_agent",
                    "status": "completed",
                    "input_lineage": f"SpineContext + FileReaderOutput + CoverageOutput + PriorClaims ({len(claim.prior_claims)})",
                    "output_lineage": (
                        f"RiskOutput(score={risk_output.fraud_risk_score:.2f}, "
                        f"fraud_flag={risk_output.is_fraud_flagged}, "
                        f"total_loss={risk_output.is_total_loss}, bi={risk_output.is_bodily_injury})"
                    ),
                    **risk_tel,
                },
                {
                    "step": "5. Agent 4: DecisionDraftAgent",
                    "type": "llm_agent",
                    "status": "completed",
                    "input_lineage": "SpineContext + FileReaderOutput + CoverageOutput + RiskOutput + 4 Post-LLM Invariants",
                    "output_lineage": (
                        f"DraftDecisionOutput(decision={draft_decision.decision.value}, "
                        f"clauses={draft_decision.cited_clauses}, "
                        f"payout=${draft_decision.payout_authorized or 0.0:,.2f})"
                    ),
                    **dd_tel,
                },
            ]
            spans = [spine_span] + agent_spans

        except Exception as e:
            logger.error(f"Agent pipeline encountered error: {e}. Engaging deterministic fallback.")
            # Deterministic Fallback: safely route to manual adjuster review
            draft_decision = DraftDecisionOutput(
                claim_id=claim.claim_id,
                decision=DecisionOutcome.ROUTE,
                decision_detail=DecisionDetail.SPECIALIST,
                reasoning=f"Pipeline exception encountered: {str(e)}. Claim routed to licensed adjuster for manual adjudication.",
                cited_clauses=["CLS-PER-001"],
                payout_authorized=None,
                verdict_source="deterministic_spine_fallback",
                requires_licensed_adjuster_confirmation=True,
            )
            file_reader_output = None
            coverage_output = None
            risk_output = None
            spans = [
                spine_span,
                {
                    "step": "2–5. LLM Agent Pipeline (Fallback)",
                    "type": "fallback",
                    "status": "fallback_triggered",
                    "latency_ms": round((time.perf_counter() - pipeline_t0) * 1000.0 - spine_ms, 1),
                    "input_lineage": f"Exception: {str(e)}",
                    "output_lineage": "Routed to specialist via deterministic_spine_fallback",
                    "prompt_tokens": 0,
                    "system_tokens": 0,
                    "schema_tokens": 0,
                    "context_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                },
            ]

        total_prompt = sum(int(s.get("prompt_tokens", 0)) for s in spans)
        total_sys = sum(int(s.get("system_tokens", 0)) for s in spans)
        total_schema = sum(int(s.get("schema_tokens", 0)) for s in spans)
        total_ctx = sum(int(s.get("context_tokens", 0)) for s in spans)
        total_out = sum(int(s.get("output_tokens", 0)) for s in spans)

        telemetry = {
            "claim_id": claim.claim_id,
            "decision": draft_decision.decision.value,
            "verdict_source": draft_decision.verdict_source,
            "total_latency_ms": round((time.perf_counter() - pipeline_t0) * 1000.0, 1),
            "total_prompt_tokens": total_prompt,
            "total_system_tokens": total_sys,
            "total_schema_tokens": total_schema,
            "total_context_tokens": total_ctx,
            "total_output_tokens": total_out,
            "total_tokens": total_prompt + total_out,
            "spans": spans,
        }

        # Step 6: Audit Record
        AuditLogger.log(
            user_id=user.user_id,
            action="adjudicate_claim",
            resource=claim.claim_id,
            outcome="granted",
            decision=draft_decision.decision.value,
            details={
                "decision_detail": draft_decision.decision_detail.value if draft_decision.decision_detail else None,
                "verdict_source": draft_decision.verdict_source,
                "cited_clauses": draft_decision.cited_clauses,
                "policy_in_force": spine_context.policy_in_force,
                "payout_authorized": draft_decision.payout_authorized,
                "total_tokens": telemetry["total_tokens"],
            },
        )

        return AdjudicationDossier(
            spine_context=spine_context,
            file_reader_output=file_reader_output,
            coverage_output=coverage_output,
            risk_output=risk_output,
            draft_decision=draft_decision,
            telemetry=telemetry,
        )
