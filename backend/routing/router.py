from typing import Dict, Any
from backend.database.models import QueryType
from backend.llm.registry import registry
from backend.config import settings

class IntelligentRouter:
    def route_query(self, query_type: QueryType, retrieval_confidence: float, context_tokens: int, risk_level: str = "LOW", conflicting_evidence: bool = False) -> Dict[str, Any]:
        """
        Determines the most cost-effective capable model based on query attributes.
        """
        
        target_tier = "standard"
        reason = "Moderate complexity standard query."
        requires_review = False
        
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
        elif query_type in [QueryType.SIMPLE_FACT, QueryType.TECHNICAL_DOCUMENTATION]:
            if retrieval_confidence > 0.5:
                target_tier = "economical"
                reason = "Simple query with high retrieval confidence."
            else:
                target_tier = "standard"
                reason = "Simple query but low retrieval confidence."
        elif query_type == QueryType.MULTI_DOCUMENT_ANALYSIS or context_tokens > 15000:
            target_tier = "advanced"
            reason = "Complex multi-document analysis or large context window."
            
        if retrieval_confidence < 0.4:
            target_tier = "advanced"
            reason += " Upgraded due to very low retrieval confidence."
            requires_review = True
            
        # Check health and fallback if necessary
        model_info = registry.get_model_info(target_tier)
        if model_info.get("health_status") == "unhealthy":
            # Try standard, then economical, then fallback
            fallback_reason = f"Original target '{target_tier}' was unhealthy. Falling back."
            return {
                "tier": "fallback",
                "reason": fallback_reason,
                "requires_review": requires_review
            }

        return {
            "tier": target_tier,
            "reason": reason,
            "requires_review": requires_review
        }

router = IntelligentRouter()
