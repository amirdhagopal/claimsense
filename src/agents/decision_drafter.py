"""
ClaimSense AI — Agent 4: DecisionDraftAgent

Synthesizes evidence from upstream agents (FileReader, Coverage, RiskAssessment)
and formulates a structured adjudication recommendation (Approve, Flag, Route, Deny).
"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.schemas import FileReaderOutput, CoverageOutput, RiskOutput, DraftDecisionOutput
from src.contracts.cms import ClaimRecord, DecisionOutcome, DecisionDetail
from src.contracts.policyadmin import PolicyRecord
from src.spine.context import SpineContext


DECISION_DRAFT_SYSTEM_PROMPT = """You are the DecisionDraftAgent in ClaimSense AI.
Your duty is to formulate the final first-pass adjudication recommendation for the licensed claims adjuster.

THE FOUR STANDARDIZED DECISION OUTCOMES (IN ORDER OF PRECEDENCE):

1. DENY ("deny") — Highest Priority:
   - If the policy has lapsed (incident date is outside effective dates), set decision="deny", detail="policy_lapsed".
   - If an exclusion applies (e.g. DUI under CLS-EXC-001, Racing under CLS-EXC-003), set decision="deny", detail="excluded_peril".
   - If vehicle VIN is not listed on schedule (CLS-COV-008), set decision="deny", detail="vehicle_not_scheduled".

2. FLAG ("flag") — Second Priority (Fraud Referral Precedence):
   - If ANY fraud indicators, narrative contradictions, damage location mismatches, or suspicious timing exist,
     you MUST choose decision="flag", detail="fraud".
   - CRITICAL: Suspected fraud or contradictions ALWAYS TAKE PRECEDENCE over routing or bodily injury claims.
     An insurer never routes or pays an injury claim if the file contains fraud indicators or physical damage contradictions!

3. ROUTE ("route") — Third Priority:
   - If NO fraud is suspected and NO exclusions apply, but:
     - Repair estimate exceeds vehicle market value (CLS-COV-006), set decision="route", detail="total_loss".
     - Serious occupant injury or hospitalisation occurred (CLS-COV-007), set decision="route", detail="bodily_injury".
     - Vehicle is classic/antique requiring specialized appraiser (CLS-COV-011), set decision="route", detail="specialist".

4. APPROVE ("approve") — Standard Covered Outcome:
   - If policy is active, loss is covered under comprehensive/collision/glass/weather (CLS-COV-001/002/003),
     and no fraud, denial, or routing triggers exist, set decision="approve", detail="standard_approval".

REASONING REQUIREMENTS:
- Your reasoning MUST be thorough, professional, and explain the factual basis.
- You MUST cite the specific clause IDs that support your determination.
- You must acknowledge that the licensed adjuster makes the final binding decision.
- Output strictly according to DraftDecisionOutput schema.
"""


class DecisionDraftAgent(BaseAgent):
    """
    Agent 4: Synthesizes findings and drafts the final recommendation dossier.
    """

    def process(
        self,
        claim: ClaimRecord,
        policy: PolicyRecord,
        file_reader_output: FileReaderOutput,
        coverage_output: CoverageOutput,
        risk_output: RiskOutput,
        spine_context: SpineContext,
    ) -> DraftDecisionOutput:
        # Check if deterministic spine mandates a rejection (e.g. lapsed policy or unscheduled vehicle)
        if spine_context.spine_must_reject:
            rejection_clause = "CLS-PER-001" if not spine_context.policy_in_force else "CLS-COV-008"
            detail = DecisionDetail.POLICY_LAPSED if not spine_context.policy_in_force else DecisionDetail.VEHICLE_NOT_SCHEDULED
            return DraftDecisionOutput(
                claim_id=claim.claim_id,
                decision=DecisionOutcome.DENY,
                decision_detail=detail,
                reasoning=f"Claim rejected deterministically: {spine_context.rejection_reason}. Grounded in policy clause {rejection_clause}.",
                cited_clauses=[rejection_clause],
                payout_authorized=0.0,
                verdict_source="model_agent",
                requires_licensed_adjuster_confirmation=True,
            )

        user_prompt = f"""
<claim_metadata>
Claim ID: {claim.claim_id}
Claimant: {claim.claimant.name}
Incident Date: {claim.incident_date}
Vehicle: {claim.vehicle.year} {claim.vehicle.make} {claim.vehicle.model} (VIN: {claim.vehicle.vin})
Market Value: ${claim.vehicle.market_value}
Repair Estimate: ${claim.repair_estimate}
</claim_metadata>

<policy_status>
Policy In Force: {spine_context.policy_in_force} (Effective: {policy.effective_date} to {policy.expiry_date})
Vehicle Scheduled on Policy: {spine_context.vehicle_scheduled}
Deductible: ${spine_context.deductible}
</policy_status>

<spine_financials>
Repair to Value Ratio: {spine_context.repair_to_value_ratio:.1%}
Is Total Loss Ratio Exceeded: {spine_context.is_constructive_total_loss}
Net Authorized Payout (net of ${spine_context.deductible} deductible): ${spine_context.max_authorized_payout}
</spine_financials>

<agent_1_file_reader>
Facts: {file_reader_output.fact_summary}
Damage Locations: {file_reader_output.damage_locations}
Contradictions: {file_reader_output.identified_contradictions}
</agent_1_file_reader>

<agent_2_coverage>
Coverage Applies: {coverage_output.coverage_applies}
Covered Perils: {coverage_output.covered_perils}
Exclusions Triggered: {coverage_output.exclusions_triggered}
Cited Clauses: {coverage_output.cited_clause_ids}
Coverage Reasoning: {coverage_output.coverage_reasoning}
</agent_2_coverage>

<agent_3_risk>
Fraud Flagged: {risk_output.is_fraud_flagged} (Score: {risk_output.fraud_risk_score})
Fraud Indicators: {risk_output.fraud_indicators}
Is Total Loss: {risk_output.is_total_loss}
Is Bodily Injury: {risk_output.is_bodily_injury}
Is Specialist Required: {risk_output.is_specialist_required}
Risk Summary: {risk_output.risk_summary}
</agent_3_risk>

Synthesize findings into a final first-pass recommendation.
"""

        decision = self.generate_typed_response(
            system_prompt=DECISION_DRAFT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=DraftDecisionOutput,
        )

        valid_exclusions = [
            e for e in coverage_output.exclusions_triggered
            if e and e.lower() not in ["none", "null", "n/a", "na", "no", "no exclusions", "[]", "none."]
        ]

        # Invariant 1: Policy Exclusions override approval/routing
        if valid_exclusions and decision.decision != DecisionOutcome.DENY:
            exc = valid_exclusions[0]
            decision = DraftDecisionOutput(
                claim_id=decision.claim_id,
                decision=DecisionOutcome.DENY,
                decision_detail=DecisionDetail.EXCLUDED_PERIL,
                reasoning=f"Claim denied due to applicable policy exclusion ({exc}): {coverage_output.coverage_reasoning}",
                cited_clauses=[exc] + [c for c in decision.cited_clauses if c != exc],
                payout_authorized=0.0,
                verdict_source="model_agent",
                requires_licensed_adjuster_confirmation=True,
            )

        # Invariant 2: Fraud Referral Precedence (Contradictions & red flags override approve/route)
        elif ((risk_output.is_fraud_flagged and risk_output.fraud_risk_score >= 0.65) or len(file_reader_output.identified_contradictions) > 0) and decision.decision not in (DecisionOutcome.DENY, DecisionOutcome.FLAG):
            reasons = file_reader_output.identified_contradictions or risk_output.fraud_indicators
            decision = DraftDecisionOutput(
                claim_id=decision.claim_id,
                decision=DecisionOutcome.FLAG,
                decision_detail=DecisionDetail.FRAUD,
                reasoning=f"Claim flagged for Special Investigation Unit (SIU) review due to detected narrative inconsistencies: {'; '.join(reasons[:2])}. {decision.reasoning}",
                cited_clauses=decision.cited_clauses or ["CLS-COV-001"],
                payout_authorized=0.0,
                verdict_source="model_agent",
                requires_licensed_adjuster_confirmation=True,
            )

        # Invariant 3: Constructive Total Loss overrides standard approval
        elif spine_context.is_constructive_total_loss and decision.decision == DecisionOutcome.APPROVE:
            decision = DraftDecisionOutput(
                claim_id=decision.claim_id,
                decision=DecisionOutcome.ROUTE,
                decision_detail=DecisionDetail.TOTAL_LOSS,
                reasoning=f"Repair estimate (${spine_context.repair_estimate:,.2f}) exceeds total loss threshold of vehicle market value (${spine_context.vehicle_market_value:,.2f}). Routed to total loss specialist under CLS-COV-006.",
                cited_clauses=["CLS-COV-006"] + [c for c in decision.cited_clauses if c != "CLS-COV-006"],
                payout_authorized=None,
                verdict_source="model_agent",
                requires_licensed_adjuster_confirmation=True,
            )

        # Invariant 4: Set authorized payout deterministically if approved
        elif decision.decision == DecisionOutcome.APPROVE:
            decision = DraftDecisionOutput(
                claim_id=decision.claim_id,
                decision=decision.decision,
                decision_detail=decision.decision_detail or DecisionDetail.STANDARD_APPROVAL,
                reasoning=decision.reasoning,
                cited_clauses=decision.cited_clauses,
                payout_authorized=spine_context.max_authorized_payout,
                verdict_source="model_agent",
                requires_licensed_adjuster_confirmation=True,
            )

        return decision
