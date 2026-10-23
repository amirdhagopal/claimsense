"""
Unit tests for Policy Clause Index & Retrieval Engine
"""

from src.contracts.policyadmin import PolicyCoverageType
from src.retrieval.policy_index import PolicyClauseIndex


def test_index_initialization():
    index = PolicyClauseIndex()
    assert len(index.clauses) > 10
    assert "CLS-PER-001" in index.clause_map
    assert "CLS-COV-001" in index.clause_map


def test_search_collision():
    index = PolicyClauseIndex()
    results = index.search(query="rear-end collision with another car on the road", top_k=3)
    clause_ids = [c.clause_id for c in results]
    assert "CLS-COV-001" in clause_ids


def test_search_hail_weather():
    index = PolicyClauseIndex()
    results = index.search(query="hail storm weather damage roof dents", top_k=3)
    clause_ids = [c.clause_id for c in results]
    assert "CLS-COV-002" in clause_ids


def test_search_exclusions():
    index = PolicyClauseIndex()
    # Racing exclusion
    results = index.search(query="racing speed trial motorsport closed circuit", top_k=3)
    clause_ids = [c.clause_id for c in results]
    assert "CLS-EXC-003" in clause_ids

    # Intoxication exclusion
    results_dui = index.search(query="intoxicated alcohol breathalyser BAC DUI", top_k=3)
    dui_ids = [c.clause_id for c in results_dui]
    assert "CLS-EXC-001" in dui_ids


def test_validate_citations():
    index = PolicyClauseIndex()
    valid, invalid = index.validate_citations(["CLS-PER-001", "CLS-COV-001", "CLS-HALLUCINATED-999"])
    assert "CLS-PER-001" in valid
    assert "CLS-COV-001" in valid
    assert "CLS-HALLUCINATED-999" in invalid
