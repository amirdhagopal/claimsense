"""
ClaimSense AI — Agent 2: CoverageAgent

Performs semantic evaluation against retrieved policy clauses and generates
defensible coverage determinations strictly citing retrieved clause IDs.
"""

from __future__ import annotations

import json
from src.agents.base import BaseAgent
from src.agents.schemas import CoverageOutput, FileReaderOutput
from src.contracts.cms import ClaimRecord
from src.contracts.policyadmin import PolicyRecord
from src.retrieval.policy_index import PolicyClauseIndex
from src.spine.context import SpineContext


COVERAGE_SYSTEM_PROMPT = """You are the CoverageAgent in ClaimSense AI.
Your duty is to determine whether the policy grants coverage for the claimed loss, or whether any exclusions apply.

GROUNDING & CITATION RULE:
You MUST ONLY cite clause IDs that appear in the <retrieved_clauses> provided below.
DO NOT invent or cite any clause ID that is not listed in the retrieved set.

EVALUATION GUIDELINES:
1. Grounding in Policy Text:
   - Accidental collisions are covered under CLS-COV-001.
   - Weather / hail damage is covered under CLS-COV-002.
   - Glass and windshield damage is covered under CLS-COV-003.
   - Theft is covered under CLS-COV-004.
   - Total loss threshold is governed by CLS-COV-006.
   - Severe bodily injury routing is governed by CLS-COV-007.
   - Classic / agreed value vehicle terms are governed by CLS-COV-010 and CLS-COV-011.
2. Exclusions:
   - If the driver was intoxicated or breathalysed above legal BAC, cite Intoxication Exclusion (CLS-EXC-001).
   - If the vehicle was racing on a track or speed trial, cite Motorsport Exclusion (CLS-EXC-003).
   - If the vehicle VIN is not on the policy schedule, cite Scheduled Vehicle Warranty (CLS-COV-008).
   - If the policy was expired on the incident date, cite Policy Period (CLS-PER-001 / CLS-PER-006).
3. Output strictly according to the CoverageOutput schema.
"""


class CoverageAgent(BaseAgent):
    """
    Agent 2: Queries searchable clause corpus and evaluates coverage applicability.
    """

    def process(
        self,
        claim: ClaimRecord,
        policy: PolicyRecord,
        file_reader_output: FileReaderOutput,
        spine_context: SpineContext,
        clause_index: PolicyClauseIndex,
    ) -> CoverageOutput:
        # 1. Retrieve relevant clauses from the searchable index
        search_query = f"{claim.incident_description} {claim.damage_description} {' '.join(file_reader_output.damage_locations)}"
        retrieved_clauses = clause_index.search(
            query=search_query,
            top_k=6,
            coverage_type=policy.coverage_type,
        )
        retrieved_clause_ids = set(c.clause_id for c in retrieved_clauses)

        retrieved_text = "\n\n".join(
            f"Clause ID: {c.clause_id}\nTitle: {c.title}\nSection: {c.section}\nText: {c.text}"
            for c in retrieved_clauses
        )

        user_prompt = f"""
<policy_terms>
Policy ID: {policy.policy_id}
Policyholder: {policy.policyholder}
Coverage Type: {policy.coverage_type.value}
Effective Date: {policy.effective_date}
Expiry Date: {policy.expiry_date}
Scheduled VINs: {policy.vehicle_schedule}
Deductible: ${policy.deductible}
Coverage Limit: ${policy.coverage_limit}
</policy_terms>

<spine_verified_facts>
Policy In Force: {spine_context.policy_in_force} (Days past expiry: {spine_context.days_past_expiry})
Vehicle VIN Scheduled: {spine_context.vehicle_scheduled}
Is Total Loss Ratio Exceeded: {spine_context.is_constructive_total_loss}
</spine_verified_facts>

<claim_facts>
Incident Date: {claim.incident_date}
Incident Description: {claim.incident_description}
Vehicle VIN: {claim.vehicle.vin}
Damage Locations: {file_reader_output.damage_locations}
Contradictions: {file_reader_output.identified_contradictions}
</claim_facts>

<retrieved_clauses>
{retrieved_text}
</retrieved_clauses>

Evaluate coverage and cite only retrieved clause IDs.
"""

        output = self.generate_typed_response(
            system_prompt=COVERAGE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=CoverageOutput,
        )

        # Grounding check: Ensure cited clauses are strictly within retrieved set
        grounded_citations = [cid for cid in output.cited_clause_ids if cid in retrieved_clause_ids]
        if not grounded_citations:
            # Fallback to the top retrieved clause if model cited outside
            grounded_citations = [retrieved_clauses[0].clause_id]

        if grounded_citations != output.cited_clause_ids:
            output = CoverageOutput(
                coverage_applies=output.coverage_applies,
                covered_perils=output.covered_perils,
                exclusions_triggered=output.exclusions_triggered,
                cited_clause_ids=grounded_citations,
                coverage_reasoning=output.coverage_reasoning,
            )

        return output
