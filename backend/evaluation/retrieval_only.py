"""LLM-free evaluation of retrieval, confidence, conflict detection and routing.

This runner deliberately does not call Hugging Face. It is safe to run when inference
credits are exhausted and isolates RAG quality from generation quality.
"""

import json
import os
import sys

from backend.database.session import SessionLocal
from backend.retrieval.analyzer import query_analyzer
from backend.retrieval.search import searcher
from backend.retrieval.confidence import confidence_analyzer
from backend.routing.router import router


EVAL_FILE = "data/evaluation/questions.json"


def run():
    if not os.path.exists(EVAL_FILE):
        print(f"Evaluation file not found: {EVAL_FILE}")
        sys.exit(1)

    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    db = SessionLocal()
    passed = 0
    try:
        print(f"Starting LLM-free retrieval evaluation of {len(questions)} questions...\n")
        for index, item in enumerate(questions, 1):
            question = item["question"]
            expected = set(item.get("expected_sources", []))
            expected_tier = item.get("expected_model_tier")
            expected_review = item.get("expected_review", False)

            analysis = query_analyzer.analyze(question)
            results, metrics = searcher.search(
                db,
                question,
                filters=analysis["filters"],
                organization_id="05a23510-ce14-4250-85d4-e2b9d6e7cbba",
            )
            confidence, level, conflict, diverse = confidence_analyzer.analyze_confidence(results)
            context_tokens = sum(len((r.get("content") or "").split()) for r in diverse)
            decision = router.route_query(
                query_type=analysis["query_type"],
                retrieval_confidence=confidence,
                context_tokens=context_tokens,
                risk_level="HIGH" if analysis["is_high_risk"] else "LOW",
                conflicting_evidence=conflict,
                query=question,
            )

            actual_sources = {r.get("document_name") for r in diverse}
            source_recall = len(expected & actual_sources) / len(expected) if expected else 1.0
            source_precision = len(expected & actual_sources) / len(actual_sources) if actual_sources else 0.0
            tier_ok = decision["tier"] == expected_tier
            review_ok = decision["requires_review"] == expected_review
            source_ok = expected.issubset(actual_sources)
            passed_case = source_ok and tier_ok and review_ok
            passed += int(passed_case)

            print(f"[{index}/{len(questions)}] {question}")
            print(f"  Sources: {sorted(actual_sources)}")
            print(f"  Recall: {source_recall:.2f} | Precision: {source_precision:.2f}")
            print(f"  Confidence: {confidence:.3f} ({level}) | Conflict: {conflict}")
            print(f"  Tier: expected {expected_tier}, actual {decision['tier']}")
            print(f"  Review: expected {expected_review}, actual {decision['requires_review']}")
            print(f"  Result: {'PASS' if passed_case else 'FAIL'}\n")

        print(f"Retrieval evaluation complete: {passed}/{len(questions)} passed.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
