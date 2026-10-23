"""
ClaimSense AI — End-to-End Adjudication Pipeline

Orchestrates the deterministic spine and the four-agent adjudication pipeline
(FileReader -> Coverage -> RiskAssessment -> DecisionDraft).
"""

from __future__ import annotations

import logging
from typing import Optional
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
    Complete dossier containing intermediate outputs and the final decision.
    """
    def __init__(
        self,
        spine_context: SpineContext,
        file_reader_output: Optional[FileReaderOutput],
        coverage_output: Optional[CoverageOutput],
        risk_output: Optional[RiskOutput],
        draft_decision: DraftDecisionOutput,
    ):
        self.spine_context = spine_context
        self.file_reader_output = file_reader_output
        self.coverage_output = coverage_output
        self.risk_output = risk_output
        self.draft_decision = draft_decision


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
        spine_context = DeterministicSpine.execute_pre_agent_checks(user, claim, policy)

        try:
            # Step 2: FileReaderAgent
            file_reader_output = self.file_reader_agent.process(
                claim=claim,
                documents=documents,
                spine_context=spine_context,
            )

            # Step 3: CoverageAgent
            coverage_output = self.coverage_agent.process(
                claim=claim,
                policy=policy,
                file_reader_output=file_reader_output,
                spine_context=spine_context,
                clause_index=self.clause_index,
            )

            # Step 4: RiskAssessmentAgent
            risk_output = self.risk_agent.process(
                claim=claim,
                documents=documents,
                file_reader_output=file_reader_output,
                coverage_output=coverage_output,
                spine_context=spine_context,
            )

            # Step 5: DecisionDraftAgent
            draft_decision = self.decision_draft_agent.process(
                claim=claim,
                policy=policy,
                file_reader_output=file_reader_output,
                coverage_output=coverage_output,
                risk_output=risk_output,
                spine_context=spine_context,
            )

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
            },
        )

        return AdjudicationDossier(
            spine_context=spine_context,
            file_reader_output=file_reader_output,
            coverage_output=coverage_output,
            risk_output=risk_output,
            draft_decision=draft_decision,
        )
