from typing import List, Dict, Any
import tiktoken
from backend.llm.registry import registry

class ContextBudgetManager:
    def __init__(self):
        # We can use a fast local tokenizer to estimate chunk tokens
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def calculate_budget(self, tier: str, prompt_tokens: int) -> int:
        model_info = registry.get_model_info(tier)
        
        context_limit = model_info.get("context_limit", 8192)
        response_reserve = model_info.get("response_token_reserve", 1000)
        safety_margin = model_info.get("token_safety_margin", 250)
        
        available_budget = context_limit - prompt_tokens - response_reserve - safety_margin
        return max(0, available_budget)

    def optimize_context(self, tier: str, prompt: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes retrieved chunks, deduplicates, and limits them to the available budget.
        """
        prompt_tokens = self.count_tokens(prompt)
        budget = self.calculate_budget(tier, prompt_tokens)
        
        # 1. Deduplicate based on text hash
        seen_texts = set()
        deduped_chunks = []
        for chunk in retrieved_chunks:
            chunk_text = chunk.get("content", "")
            if chunk_text not in seen_texts:
                seen_texts.add(chunk_text)
                deduped_chunks.append(chunk)
                
        # 2. Fit into budget (assuming already ranked)
        final_chunks = []
        current_used_budget = 0
        original_context_tokens = 0
        
        # Calculate original
        for chunk in retrieved_chunks:
            original_context_tokens += self.count_tokens(chunk.get("content", ""))
            
        for chunk in deduped_chunks:
            tokens = self.count_tokens(chunk.get("content", ""))
            if current_used_budget + tokens <= budget:
                final_chunks.append(chunk)
                current_used_budget += tokens
            else:
                # We reached the budget limit
                break
                
        tokens_saved = original_context_tokens - current_used_budget
        compression_ratio = 0.0
        if original_context_tokens > 0:
            compression_ratio = tokens_saved / original_context_tokens
            
        return {
            "optimized_chunks": final_chunks,
            "original_context_tokens": original_context_tokens,
            "optimized_context_tokens": current_used_budget,
            "tokens_saved": tokens_saved,
            "compression_ratio": round(compression_ratio, 4)
        }

context_budget_manager = ContextBudgetManager()
