import unittest
from backend.retrieval.analyzer import query_analyzer
from backend.retrieval.confidence import confidence_analyzer
from backend.routing.router import router
from backend.database.models import QueryType

class TestRetrievalComponents(unittest.TestCase):
    
    def test_query_analyzer(self):
        query = "What is the settlement policy for Partner A in July for Compliance?"
        result = query_analyzer.analyze(query)
        
        self.assertEqual(result["filters"]["partner"], "Partner A")
        self.assertEqual(result["filters"]["month"], "July")
        self.assertEqual(result["filters"]["business_domain"], "Compliance")
        self.assertTrue(result["is_high_risk"])
        self.assertEqual(result["query_type"], "HIGH_RISK")

    def test_confidence_and_conflict_detection(self):
        # Mock results with varying scores and a conflict in rules
        results = [
            {"document_name": "doc1.pdf", "score": 0.95, "content": "The settlement window is T+1 days."},
            {"document_name": "doc2.pdf", "score": 0.90, "content": "The settlement window is T+2 days."}
        ]
        
        top_score, level, has_conflict, diverse = confidence_analyzer.analyze_confidence(results)
        
        self.assertEqual(top_score, 0.95)
        self.assertTrue(has_conflict) # T+1 vs T+2
        self.assertEqual(level, "MEDIUM") # Downgraded from HIGH due to conflict

    def test_intelligent_router_conflict(self):
        # Even if it's a simple fact query, if there's conflicting evidence, it should route to advanced and require review
        decision = router.route_query(
            query_type=QueryType.SIMPLE_FACT,
            retrieval_confidence=0.95,
            context_tokens=1000,
            risk_level="LOW",
            conflicting_evidence=True
        )
        
        self.assertEqual(decision["tier"], "advanced")
        self.assertTrue(decision["requires_review"])

if __name__ == '__main__':
    unittest.main()
