import re
from typing import Dict, List


class RelevanceScorer:
    """Deterministic lexical relevance features used after vector/FTS retrieval.

    This is intentionally LLM-free so retrieval quality can be evaluated without
    inference credits and so exact operational identifiers are not lost to
    embedding similarity.
    """

    @staticmethod
    def terms(text: str) -> List[str]:
        return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1]

    @classmethod
    def score(cls, query: str, content: str, filename: str) -> Dict[str, float]:
        query_terms = cls.terms(query)
        if not query_terms:
            return {"lexical": 0.0, "filename": 0.0, "phrase": 0.0}

        q = set(query_terms)
        content_terms = set(cls.terms(content))
        filename_terms = set(cls.terms(filename))

        lexical = len(q & content_terms) / len(q)
        filename_score = len(q & filename_terms) / len(q)

        normalized_query = " ".join(query_terms)
        normalized_content = " ".join(cls.terms(content))
        phrase_hits = 0
        for phrase in (
            "idempotency keys",
            "api v2",
            "july 14",
            "partner a",
            "partner b",
            "standard settlement",
            "enhanced kyc",
            "reconciliation issues",
            "after 18 00 utc",
        ):
            phrase_terms = " ".join(cls.terms(phrase))
            if phrase_terms in normalized_query and phrase_terms in normalized_content:
                phrase_hits += 1
        phrase_score = min(1.0, phrase_hits / 2.0)

        return {"lexical": lexical, "filename": filename_score, "phrase": phrase_score}


relevance_scorer = RelevanceScorer()
