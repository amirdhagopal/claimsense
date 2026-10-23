"""
ClaimSense AI — Agent 3: RiskAssessmentAgent

Evaluates multi-document narrative consistency, fraud indicators,
constructive total loss economics, and severe bodily injury exposure.
"""

from __future__ import annotations

from src.agents.base import BaseAgent
from src.agents.schemas import FileReaderOutput, CoverageOutput, RiskOutput
from src.contracts.cms import ClaimRecord
from src.contracts.docstore import DocumentContentResponse
from src.spine.context import SpineContext


RISK_SYSTEM_PROMPT = """You are the RiskAssessmentAgent in ClaimSense AI.
Your duty is to assess risk dimensions: fraud risk, total loss economics, bodily injury severity, and specialist needs.

RISK EVALUATION CRITERIA:
1. Fraud Referral (Flag/Refer):
   You MUST flag for fraud (is_fraud_flagged = True, fraud_risk_score >= 0.75) if ANY of the following exist:
   - FileReader detected contradictions (e.g. damage location mismatch, rear vs front, medical contradiction, whiplash in unoccupied car, airbag burns without deployment).
   - Physical contradiction: Claimant says rear-ended while parked, but repair estimate / photos show front-end damage.
   - Medical contradiction: Claimant reports airbag burns or whiplash, but ECU vehicle diagnostics show NO airbags deployed.
   - Suspicious timing: Policy was upgraded to Comprehensive or limits increased within 72 hours before a high-value theft or total loss claim.
   - Staged collision: Vehicles involved trace to the same household/family, with low-speed minor damage coupled with exorbitant medical claims.
2. Normal Road Losses (NOT Fraud):
   - Standard rock strikes, windshield cracks, road debris, hail, weather, and parking lot scrapes are ordinary losses.
   - For standard losses without physical contradictions or staged collision indicators, you MUST set is_fraud_flagged = False and fraud_risk_score <= 0.20.
3. Constructive Total Loss (Route):
   - Set is_total_loss = True if repair estimate exceeds 75% of vehicle market value, or if severe frame/rollover damage is described.
4. Bodily Injury Specialist (Route):
   - Set is_bodily_injury = True if documents mention hospitalisation, ICU, broken bones, punctured lung, or serious physical injury to any occupant.
5. Classic / Specialist Vehicle (Route):
   - Set is_specialist_required = True if vehicle is classic/antique (e.g., 1967 Jaguar E-Type) requiring specialist appraisal.
6. Output strictly according to the RiskOutput schema.
"""


class RiskAssessmentAgent(BaseAgent):
    """
    Agent 3: Assesses fraud indicators, total loss economics, and bodily injury severity.
    """

    def process(
        self,
        claim: ClaimRecord,
        documents: list[DocumentContentResponse],
        file_reader_output: FileReaderOutput,
        coverage_output: CoverageOutput,
        spine_context: SpineContext,
    ) -> RiskOutput:
        doc_flags = []
        for d in documents:
            if "flags" in d.structured_data:
                doc_flags.extend(d.structured_data["flags"])

        user_prompt = f"""
<claim_details>
Claim ID: {claim.claim_id}
Incident Date & Time: {claim.incident_date} {claim.incident_time or ''}
Location: {claim.incident_location}
Description: {claim.incident_description}
Vehicle: {claim.vehicle.year} {claim.vehicle.make} {claim.vehicle.model}
Market Value: ${claim.vehicle.market_value}
Repair Estimate: ${claim.repair_estimate}
Repair-to-Value Ratio: {spine_context.repair_to_value_ratio:.1%}
Spine Total Loss Flag: {spine_context.is_constructive_total_loss}
Prior Claims Count: {len(claim.prior_claims)}
</claim_details>

<file_reader_findings>
Damaged Locations: {file_reader_output.damage_locations}
Contradictions Identified: {file_reader_output.identified_contradictions}
Unwitnessed Loss: {file_reader_output.unwitnessed_loss}
Injuries Reported: {file_reader_output.injuries_reported}
</file_reader_findings>

<coverage_findings>
Coverage Applies: {coverage_output.coverage_applies}
Cited Clauses: {coverage_output.cited_clause_ids}
Exclusions: {coverage_output.exclusions_triggered}
</coverage_findings>

<document_summaries>
{chr(10).join(f"- {d.document_type.value}: {d.content_summary}" for d in documents)}
</document_summaries>

Evaluate fraud, total loss, bodily injury, and specialist routing triggers.
"""

        return self.generate_typed_response(
            system_prompt=RISK_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=RiskOutput,
        )
