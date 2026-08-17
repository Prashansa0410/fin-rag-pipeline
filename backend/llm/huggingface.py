from typing import Dict, Any
from .provider import LLMProvider
from huggingface_hub import AsyncInferenceClient
from backend.config import settings


class HuggingFaceProvider(LLMProvider):
    """Hugging Face Inference Providers adapter using the official async SDK."""

    def __init__(self):
        self.client = AsyncInferenceClient(provider="auto", token=settings.HF_TOKEN)

    async def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 1024),
            temperature=kwargs.get("temperature", 0.7),
        )

        answer = response.choices[0].message.content if response.choices else ""
        usage_info = response.usage
        estimated_cost = getattr(usage_info, "estimated_cost", None) if usage_info else None

        return {
            "answer": answer.strip() if answer else "",
            "usage": {
                "input_tokens": getattr(usage_info, "prompt_tokens", 0) or 0,
                "output_tokens": getattr(usage_info, "completion_tokens", 0) or 0,
                "total_tokens": getattr(usage_info, "total_tokens", 0) or 0,
                "estimated_cost": estimated_cost,
            },
        }

    async def health_check(self, model: str) -> bool:
        try:
            await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return True
        except Exception:
            return False


huggingface_provider = HuggingFaceProvider()
