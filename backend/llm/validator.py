import json
from typing import List, Dict, Any, Tuple
from backend.llm.registry import registry
from backend.llm.huggingface import huggingface_provider
import time

class GroundingValidator:
    def __init__(self):
        # We use the economical tier for validation to keep costs low
        self.validation_tier = "economical"

    def _build_validation_prompt(self, question: str, answer: str, context_chunks: List[Dict[str, Any]]) -> str:
        context_text = "\n\n".join([f"Source {i+1}:\n{c['content']}" for i, c in enumerate(context_chunks)])
        
        prompt = f"""You are a strict Grounding Validator for a financial research AI.
Your job is to verify that the generated answer is fully supported by the provided context chunks.

CONTEXT:
{context_text}

QUESTION:
{question}

GENERATED ANSWER:
{answer}

INSTRUCTIONS:
Evaluate the GENERATED ANSWER against the CONTEXT.
1. Are all factual claims supported by the CONTEXT?
2. Are there any hallucinations (information not in the CONTEXT)?
3. If the CONTEXT contains conflicting information, did the ANSWER acknowledge it?

Respond ONLY with a valid JSON object in this exact format:
{{
    "is_grounded": true/false,
    "reason": "Brief explanation of why it is or isn't grounded",
    "unsupported_claims": ["List any unsupported claims here, or empty array"]
}}
"""
        return prompt

    async def validate_grounding(self, question: str, answer: str, context_chunks: List[Dict[str, Any]]) -> Tuple[bool, str, float]:
        """
        Validates the generated answer against the retrieved evidence.
        Returns: (is_grounded, reason, latency_ms)
        """
        prompt = self._build_validation_prompt(question, answer, context_chunks)
        
        model_info = registry.get_model_info(self.validation_tier)
        model_id = model_info["model_id"]
        
        t0 = time.perf_counter()
        try:
            response_obj = await huggingface_provider.generate(model_id, prompt, max_tokens=150, temperature=0.0)
            response_text = response_obj["answer"]
            t1 = time.perf_counter()
            
            # Extract JSON from response
            # Some models might wrap it in ```json ... ```
            json_str = response_text
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
                
            result = json.loads(json_str)
            
            is_grounded = result.get("is_grounded", False)
            reason = result.get("reason", "Failed to parse validation reason.")
            
            return is_grounded, reason, (t1 - t0) * 1000
            
        except Exception as e:
            # If validation fails due to parsing or API error, we default to False for safety
            t1 = time.perf_counter()
            return False, f"Validation system error: {str(e)}", (t1 - t0) * 1000

grounding_validator = GroundingValidator()
