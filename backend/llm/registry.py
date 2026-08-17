from typing import Dict, Any
from backend.config import settings
from .provider import LLMProvider
from .huggingface import HuggingFaceProvider


class ModelRegistry:
    """Runtime model metadata used by routing, budgeting and cost accounting."""

    def __init__(self):
        self.models = {
            "economical": {"model_id": settings.ECONOMICAL_MODEL, "provider": "huggingface", "tier": "economical", "display_name": "Economical", "capability_score": 0.60, "latency_class": "low", "context_limit": 32768, "input_cost": 0.0001, "output_cost": 0.0002, "response_token_reserve": 1000, "token_safety_margin": 250, "health_status": "unknown"},
            "standard": {"model_id": settings.STANDARD_MODEL, "provider": "huggingface", "tier": "standard", "display_name": "Standard", "capability_score": 0.85, "latency_class": "medium", "context_limit": 32768, "input_cost": 0.001, "output_cost": 0.002, "response_token_reserve": settings.RESPONSE_TOKEN_RESERVE, "token_safety_margin": settings.TOKEN_SAFETY_MARGIN, "health_status": "unknown"},
            # HF Router reported $0.38/M input and $0.40/M output for the currently
            # verified Qwen2.5-72B provider, represented here as $/1K tokens.
            "advanced": {"model_id": settings.ADVANCED_MODEL, "provider": "huggingface", "tier": "advanced", "display_name": "Advanced", "capability_score": 0.98, "latency_class": "high", "context_limit": 32768, "input_cost": 0.00038, "output_cost": 0.00040, "response_token_reserve": 3000, "token_safety_margin": 1000, "health_status": "unknown"},
            "fallback": {"model_id": settings.FALLBACK_MODEL, "provider": "huggingface", "tier": "fallback", "display_name": "Fallback", "capability_score": 0.60, "latency_class": "low", "context_limit": 32768, "input_cost": 0.0001, "output_cost": 0.0002, "response_token_reserve": 1000, "token_safety_margin": 250, "health_status": "unknown"},
        }
        self.providers: Dict[str, LLMProvider] = {"huggingface": HuggingFaceProvider()}

    def get_model_info(self, tier: str) -> Dict[str, Any]:
        return self.models.get(tier, self.models["fallback"])

    def get_provider(self, provider_name: str) -> LLMProvider:
        return self.providers.get(provider_name, self.providers["huggingface"])

    def update_health(self, tier: str, is_healthy: bool):
        if tier in self.models:
            self.models[tier]["health_status"] = "healthy" if is_healthy else "unhealthy"


registry = ModelRegistry()
