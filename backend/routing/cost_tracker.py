from typing import Dict
from backend.llm.registry import registry

class CostTracker:
    def calculate_cost(self, tier: str, input_tokens: int, output_tokens: int) -> float:
        model_info = registry.get_model_info(tier)
        input_cost = model_info.get("input_cost", 0.0)
        output_cost = model_info.get("output_cost", 0.0)
        
        return (input_tokens / 1000) * input_cost + (output_tokens / 1000) * output_cost

    def estimate_savings(self, selected_tier: str, input_tokens: int, output_tokens: int, 
                         original_context_tokens: int = 0, cache_hit: bool = False, 
                         baseline_tier: str = "advanced") -> Dict[str, float]:
        
        # 1. Calculate the baseline cost as if we used the baseline model for the ORIGINAL context size
        baseline_cost = self.calculate_cost(baseline_tier, original_context_tokens + (input_tokens - original_context_tokens), output_tokens)
        
        # 2. Actual estimated cost for the current model
        actual_cost = 0.0 if cache_hit else self.calculate_cost(selected_tier, input_tokens, output_tokens)
        
        # 3. Routing Savings (savings from using a cheaper model)
        # Assumes context optimization wasn't done yet to isolate routing impact
        routing_cost_without_optimization = self.calculate_cost(selected_tier, original_context_tokens + (input_tokens - original_context_tokens), output_tokens)
        routing_savings = baseline_cost - routing_cost_without_optimization
        
        # 4. Context Optimization Savings (savings purely from reducing tokens)
        context_optimization_savings = routing_cost_without_optimization - self.calculate_cost(selected_tier, input_tokens, output_tokens)
        
        # 5. Cache Savings (if hit, we saved the actual cost)
        cache_savings = self.calculate_cost(selected_tier, input_tokens, output_tokens) if cache_hit else 0.0
        
        total_savings = routing_savings + context_optimization_savings + cache_savings
        
        return {
            "baseline_cost": round(baseline_cost, 6),
            "actual_estimated_cost": round(actual_cost, 6),
            "routing_savings": round(max(0, routing_savings), 6),
            "context_optimization_savings": round(max(0, context_optimization_savings), 6),
            "cache_savings": round(max(0, cache_savings), 6),
            "total_estimated_savings": round(max(0, total_savings), 6)
        }

cost_tracker = CostTracker()
