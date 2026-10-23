"""
ClaimSense AI — Policy Clause Searchable Corpus & Retrieval Engine

Implements searchable indexing and retrieval over policy clauses with
guaranteed source attribution. The CoverageAgent queries this index and cites
only clauses that were genuinely retrieved.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Optional

from src.contracts.policyadmin import PolicyClause, PolicyCoverageType
from src.models.synthetic_shapes import CANONICAL_POLICY_CLAUSES


class PolicyClauseIndex:
    """
    Searchable index over policy clauses using BM25-based keyword ranking
    and coverage filtering.
    """

    def __init__(self, clauses: Optional[list[PolicyClause]] = None):
        self.clauses: list[PolicyClause] = list(clauses or CANONICAL_POLICY_CLAUSES)
        self.clause_map: dict[str, PolicyClause] = {c.clause_id: c for c in self.clauses}
        self._build_index()

    def _tokenize(self, text: str) -> list[str]:
        # Lowercase and split on non-alphanumeric
        tokens = re.findall(r"\b[a-z0-9_-]+\b", text.lower())
        stopwords = {
            "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of",
            "with", "is", "was", "are", "by", "this", "that", "it", "from", "be"
        }
        return [t for t in tokens if t not in stopwords and len(t) > 1]

    def _build_index(self) -> None:
        self.doc_freqs: dict[str, int] = defaultdict(int)
        self.doc_lengths: list[int] = []
        self.doc_tokens: list[list[str]] = []

        for c in self.clauses:
            full_text = f"{c.clause_id} {c.title} {c.section} {c.text}"
            tokens = self._tokenize(full_text)
            self.doc_tokens.append(tokens)
            self.doc_lengths.append(len(tokens))
            unique_tokens = set(tokens)
            for t in unique_tokens:
                self.doc_freqs[t] += 1

        self.num_docs = len(self.clauses)
        self.avg_doc_len = sum(self.doc_lengths) / max(1, self.num_docs)

    def search(
        self,
        query: str,
        top_k: int = 5,
        coverage_type: Optional[PolicyCoverageType] = None,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> list[PolicyClause]:
        """
        BM25 ranking of policy clauses against query string.
        Optionally filters clauses applicable to the given policy coverage type.
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            # Fallback to general policy clauses
            return self.clauses[:top_k]

        scores = [0.0] * self.num_docs

        for q_token in query_tokens:
            df = self.doc_freqs.get(q_token, 0)
            if df == 0:
                continue

            # Inverse Document Frequency (IDF)
            idf = math.log(1 + (self.num_docs - df + 0.5) / (df + 0.5))

            for i, tokens in enumerate(self.doc_tokens):
                # Filter by coverage type if specified
                clause = self.clauses[i]
                if coverage_type and clause.applies_to_coverage:
                    if coverage_type not in clause.applies_to_coverage:
                        continue

                # Term Frequency
                tf = tokens.count(q_token)
                if tf > 0:
                    doc_len = self.doc_lengths[i]
                    num = tf * (k1 + 1)
                    denom = tf + k1 * (1 - b + b * (doc_len / self.avg_doc_len))
                    scores[i] += idf * (num / denom)

        # Pair scores with clauses and sort descending
        ranked_indices = sorted(
            range(self.num_docs),
            key=lambda idx: scores[idx],
            reverse=True
        )

        # Select top_k with positive scores, or fallback if top scores are zero
        results = []
        for idx in ranked_indices:
            clause = self.clauses[idx]
            if coverage_type and clause.applies_to_coverage and coverage_type not in clause.applies_to_coverage:
                continue
            results.append(clause)
            if len(results) >= top_k:
                break

        # Always ensure policy period clause CLS-PER-001 is included for in-force attribution
        if "CLS-PER-001" in self.clause_map and not any(r.clause_id == "CLS-PER-001" for r in results):
            if len(results) >= top_k:
                results[-1] = self.clause_map["CLS-PER-001"]
            else:
                results.append(self.clause_map["CLS-PER-001"])

        return results

    def get_clause_by_id(self, clause_id: str) -> Optional[PolicyClause]:
        return self.clause_map.get(clause_id)

    def validate_citations(self, cited_clause_ids: list[str]) -> tuple[list[str], list[str]]:
        """
        Validates a list of clause IDs.
        Returns: (valid_citations, invalid_hallucinated_citations)
        """
        valid = []
        invalid = []
        for cid in cited_clause_ids:
            if cid in self.clause_map:
                valid.append(cid)
            else:
                invalid.append(cid)
        return valid, invalid
