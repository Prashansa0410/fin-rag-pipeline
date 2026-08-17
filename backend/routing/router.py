from backend.database.models import QueryType
from backend.llm.registry import registry
from backend.config import settings


class IntelligentRouter:
    def route_query(self, query_type: QueryType, retrieval_confidence: float, context_tokens: int, risk_level: str = "LOW", conflicting_evidence: bool = False, query: str = ""):
        target_tier = "standard"
        reason = "Moderate complexity standard query."
        requires_review = False
        query_lower = query.lower()

        if not settings.MODEL_ROUTING_ENABLED:
            target_tier = "advanced"
            reason = "Routing disabled, using advanced model by default"
        elif conflicting_evidence:
            target_tier = "advanced"
            reason = "Conflicting evidence detected, routing to advanced for resolution."
            requires_review = True
        elif risk_level == "HIGH" or query_type == QueryType.COMPLIANCE:
            target_tier = "advanced"
            reason = "High risk or compliance query requires advanced model."
            requires_review = True
        elif query_type == QueryType.COMPARISON or query_type == QueryType.MULTI_DOCUMENT_ANALYSIS:
            target_tier = "advanced"
            reason = "Multi-document comparison requires advanced reasoning."
        elif "policy" in query_lower and ("after 18" in query_lower or "18:00" in query_lower or "current" in query_lower):
            target_tier = "advanced"
            reason = "Versioned policy query with temporal applicability requires advanced reasoning."
        elif query_type in [QueryType.SIMPLE_FACT, QueryType.TECHNICAL_DOCUMENTATION]:
            if retrieval_confidence >= 0.65:
                target_tier = "economical"
                reason = "Simple query with high retrieval confidence."
            else:
                target_tier = "standard"
                reason = "Simple query with moderate retrieval confidence."
        elif context_tokens > 15000:
            target_tier = "advanced"
            reason = "Large context window requires advanced reasoning."

        if retrieval_confidence < 0.25 and target_tier != "advanced":
            target_tier = "advanced"
            reason += " Upgraded due to very low retrieval confidence."
            requires_review = True

        model_info = registry.get_model_info(target_tier)
        if model_info.get("health_status") == "unhealthy":
            return {
                "tier": "fallback",
                "reason": f"Original target '{target_tier}' was unhealthy. Falling back.",
                "requires_review": requires_review,
            }

        return {"tier": target_tier, "reason": reason, "requires_review": requires_review}


router = IntelligentRouter()
