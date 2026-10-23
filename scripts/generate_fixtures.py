"""
ClaimSense AI — Synthetic Fixture Generator & Validation Script

Converts evaluation cases into fully validated synthetic fixtures conforming
to the CMS, DocStore, and PolicyAdmin typed Pydantic contracts.
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, date

from src.contracts.cms import ClaimRecord, ClaimantInfo, VehicleInfo, PriorClaimRecord, ClaimStatus
from src.contracts.docstore import DocumentMetadata, DocumentContentResponse, DocumentType
from src.contracts.policyadmin import PolicyRecord, PolicyClause, PolicyCoverageType
from src.models.synthetic_shapes import CANONICAL_POLICY_CLAUSES, SyntheticClaimDossier

BASE_DIR = Path(__file__).resolve().parent.parent
EVALS_FILE = BASE_DIR / "evals" / "cases" / "milestone1_cases.json"
FIXTURES_DIR = BASE_DIR / "data" / "fixtures"


def map_doc_type(raw_type: str) -> DocumentType:
    mapping = {
        "police_report": DocumentType.POLICE_REPORT,
        "repair_estimate": DocumentType.REPAIR_ESTIMATE,
        "photo": DocumentType.PHOTO,
        "medical_report": DocumentType.MEDICAL_REPORT,
        "weather_report": DocumentType.WEATHER_REPORT,
        "policy_endorsement": DocumentType.POLICY_ENDORSEMENT,
        "vehicle_diagnostic": DocumentType.VEHICLE_DIAGNOSTIC,
        "witness_statement": DocumentType.WITNESS_STATEMENT,
        "incident_report": DocumentType.INCIDENT_REPORT,
    }
    return mapping.get(raw_type, DocumentType.POLICE_REPORT)


def map_coverage_type(raw_type: str) -> PolicyCoverageType:
    mapping = {
        "Comprehensive": PolicyCoverageType.COMPREHENSIVE,
        "Third-Party Only": PolicyCoverageType.THIRD_PARTY_ONLY,
        "Collision Only": PolicyCoverageType.COLLISION_ONLY,
        "Agreed Value - Classic": PolicyCoverageType.AGREED_VALUE_CLASSIC,
    }
    return mapping.get(raw_type, PolicyCoverageType.COMPREHENSIVE)


def main() -> int:
    print(f"Reading evaluation cases from {EVALS_FILE}...")
    with open(EVALS_FILE, "r") as f:
        cases = json.load(f)

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    dossiers = []

    for case in cases:
        c_data = case["claim"]
        p_data = case["policy"]
        docs_data = case["documents"]
        expected = case["expected"]

        # Parse Claim
        claim = ClaimRecord(
            claim_id=c_data["claim_id"],
            claimant=ClaimantInfo(
                name=c_data["claimant"]["name"],
                policy_id=c_data["claimant"]["policy_id"],
                contact=c_data["claimant"]["contact"],
            ),
            status=ClaimStatus.NEW,
            incident_date=date.fromisoformat(c_data["incident_date"]),
            incident_time=c_data.get("incident_time"),
            incident_location=c_data["incident_location"],
            incident_description=c_data["incident_description"],
            vehicle=VehicleInfo(
                make=c_data["vehicle"]["make"],
                model=c_data["vehicle"]["model"],
                year=c_data["vehicle"]["year"],
                vin=c_data["vehicle"]["vin"],
                market_value=float(c_data["vehicle"]["market_value"]),
            ),
            damage_description=c_data["damage_description"],
            repair_estimate=float(c_data["repair_estimate"]),
            prior_claims=[
                PriorClaimRecord(
                    claim_id=pc["claim_id"],
                    incident_date=date.fromisoformat(pc["date"]),
                    outcome=pc["outcome"],
                    amount_paid=float(pc["amount"]),
                )
                for pc in c_data.get("prior_claims", [])
            ],
            assigned_adjuster_id=case.get("requesting_user", {}).get("user_id", "adjuster-jane"),
        )

        # Parse Policy Clauses
        clauses = []
        for cl in p_data.get("clauses", []):
            clauses.append(
                PolicyClause(
                    clause_id=cl["clause_id"],
                    title=cl["title"],
                    section="Coverage" if "COV" in cl["clause_id"] else ("Period" if "PER" in cl["clause_id"] else ("Exclusion" if "EXC" in cl["clause_id"] else "Deductible")),
                    text=cl["text"],
                    applies_to_coverage=[map_coverage_type(p_data["coverage_type"])],
                )
            )

        # Parse Policy
        policy = PolicyRecord(
            policy_id=p_data["policy_id"],
            policyholder=p_data["policyholder"],
            effective_date=date.fromisoformat(p_data["effective_date"]),
            expiry_date=date.fromisoformat(p_data["expiry_date"]),
            status=p_data["status"],
            coverage_type=map_coverage_type(p_data["coverage_type"]),
            vehicle_schedule=p_data["vehicle_schedule"],
            clauses=clauses,
            deductible=float(p_data.get("deductible", 500.0)),
            coverage_limit=float(p_data.get("coverage_limit", 50000.0)),
        )

        # Parse Documents
        documents = []
        for d in docs_data:
            documents.append(
                DocumentContentResponse(
                    doc_id=d["doc_id"],
                    claim_id=c_data["claim_id"],
                    document_type=map_doc_type(d["type"]),
                    content_summary=d["content_summary"],
                    structured_data={},
                    is_redacted=False,
                )
            )

        dossier = SyntheticClaimDossier(
            claim=claim,
            policy=policy,
            documents=documents,
            ground_truth_decision=expected["decision"],
            ground_truth_fraud=expected.get("fraud_ground_truth", False),
            ground_truth_detail=expected.get("decision_detail"),
            expected_citations=expected.get("cited_clauses", []),
        )
        dossiers.append(dossier)

    # Save to data/fixtures/synthetic_dossiers.json
    output_file = FIXTURES_DIR / "synthetic_dossiers.json"
    with open(output_file, "w") as f:
        f.write(json.dumps([d.model_dump(mode="json") for d in dossiers], indent=2))

    print(f"✅ Successfully converted and validated {len(dossiers)} synthetic dossiers into {output_file}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
