"""
ClaimSense AI — Evaluation Suite Runner (Scaffold)

This script validates evaluation cases against the JSON schema and reports
the distribution of cases across decision outcomes and adversarial families.

In Milestone 3, this will be extended to execute cases against the live agent
pipeline and report pass/fail with per-criterion metrics. The CI gate will
call this script; non-zero exit blocks the image push.
"""

import json
import sys
from pathlib import Path
from collections import Counter


EVALS_DIR = Path(__file__).parent
CASES_DIR = EVALS_DIR / "cases"
SCHEMA_PATH = EVALS_DIR / "schema.json"

REQUIRED_FIELDS = [
    "case_id", "version", "category", "description",
    "claim", "policy", "documents", "expected"
]

VALID_DECISIONS = {"approve", "flag", "route", "deny"}
VALID_CATEGORIES = {"standard", "adversarial", "edge_case"}
VALID_ADVERSARIAL_FAMILIES = {
    "prompt_injection", "cross_record_leakage",
    "forced_auto_decision", "narrative_contradiction",
    "boundary_manipulation", None
}


def load_cases(filepath: Path) -> list[dict]:
    """Load evaluation cases from a JSON file."""
    with open(filepath) as f:
        cases = json.load(f)
    if not isinstance(cases, list):
        raise ValueError(f"Expected a JSON array in {filepath}")
    return cases


def validate_case(case: dict, index: int) -> list[str]:
    """Validate a single evaluation case. Returns a list of error messages."""
    errors = []
    case_id = case.get("case_id", f"<index {index}>")

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in case:
            errors.append(f"{case_id}: missing required field '{field}'")

    # Validate decision
    decision = case.get("expected", {}).get("decision")
    if decision and decision not in VALID_DECISIONS:
        errors.append(f"{case_id}: invalid decision '{decision}', must be one of {VALID_DECISIONS}")

    # Validate category
    category = case.get("category")
    if category and category not in VALID_CATEGORIES:
        errors.append(f"{case_id}: invalid category '{category}', must be one of {VALID_CATEGORIES}")

    # Validate adversarial family
    family = case.get("adversarial_family")
    if family not in VALID_ADVERSARIAL_FAMILIES:
        errors.append(f"{case_id}: invalid adversarial_family '{family}'")

    # Adversarial cases must have a family
    if category == "adversarial" and family is None:
        errors.append(f"{case_id}: adversarial case must specify an adversarial_family")

    # Check that reasoning constraints are lists
    expected = case.get("expected", {})
    for key in ["reasoning_must_contain", "reasoning_must_not_contain", "cited_clauses"]:
        val = expected.get(key)
        if val is not None and not isinstance(val, list):
            errors.append(f"{case_id}: expected.{key} must be a list")

    # Check that claim has required sub-fields
    claim = case.get("claim", {})
    for field in ["claim_id", "claimant", "incident_date", "incident_description", "vehicle", "damage_description", "repair_estimate"]:
        if field not in claim:
            errors.append(f"{case_id}: claim missing required field '{field}'")

    # Check that policy has required sub-fields
    policy = case.get("policy", {})
    for field in ["policy_id", "policyholder", "effective_date", "expiry_date", "status", "coverage_type", "clauses"]:
        if field not in policy:
            errors.append(f"{case_id}: policy missing required field '{field}'")

    return errors


def report_distribution(cases: list[dict]) -> None:
    """Print a summary of the case distribution."""
    decision_counts = Counter(c["expected"]["decision"] for c in cases)
    category_counts = Counter(c["category"] for c in cases)
    family_counts = Counter(
        c.get("adversarial_family")
        for c in cases
        if c["category"] == "adversarial"
    )

    print("\n" + "=" * 60)
    print("EVALUATION SUITE — CASE DISTRIBUTION")
    print("=" * 60)

    print(f"\nTotal cases: {len(cases)}")

    print("\nBy decision outcome:")
    for decision in ["approve", "deny", "flag", "route"]:
        count = decision_counts.get(decision, 0)
        bar = "█" * count
        print(f"  {decision:>8}: {count:>2}  {bar}")

    print("\nBy category:")
    for category in ["standard", "adversarial", "edge_case"]:
        count = category_counts.get(category, 0)
        if count > 0:
            print(f"  {category:>12}: {count}")

    print("\nAdversarial families:")
    for family, count in sorted(family_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {family:>25}: {count}")

    # Check for fraud ground truth distribution
    fraud_true = sum(1 for c in cases if c["expected"].get("fraud_ground_truth") is True)
    fraud_false = sum(1 for c in cases if c["expected"].get("fraud_ground_truth") is False)
    print(f"\nFraud ground truth: {fraud_true} true, {fraud_false} false")

    # Check spine rejection cases
    spine_reject = sum(1 for c in cases if c["expected"].get("spine_must_reject") is True)
    print(f"Spine rejection cases: {spine_reject}")

    print("=" * 60)


def main() -> int:
    """Main entry point. Returns 0 on success, 1 on validation failure."""
    # Find all case files
    case_files = sorted(CASES_DIR.glob("*.json"))
    if not case_files:
        print("ERROR: No case files found in evals/cases/")
        return 1

    all_cases = []
    all_errors = []

    for filepath in case_files:
        print(f"Loading {filepath.name}...")
        try:
            cases = load_cases(filepath)
            for i, case in enumerate(cases):
                errors = validate_case(case, i)
                all_errors.extend(errors)
            all_cases.extend(cases)
        except (json.JSONDecodeError, ValueError) as e:
            all_errors.append(f"{filepath.name}: {e}")

    # Check for duplicate case IDs
    case_ids = [c.get("case_id") for c in all_cases]
    duplicates = [cid for cid, count in Counter(case_ids).items() if count > 1]
    if duplicates:
        all_errors.append(f"Duplicate case IDs: {duplicates}")

    # Report
    if all_errors:
        print(f"\n❌ VALIDATION FAILED — {len(all_errors)} error(s):")
        for err in all_errors:
            print(f"  • {err}")
        return 1

    print(f"\n✅ All {len(all_cases)} cases passed validation.")
    report_distribution(all_cases)
    return 0


if __name__ == "__main__":
    sys.exit(main())
