import os
from typing import Dict, Any
from .provider import LLMProvider
from huggingface_hub import AsyncInferenceClient
from backend.config import settings

class HuggingFaceProvider(LLMProvider):
    def __init__(self):
        # Using the official SDK and setting provider="auto" matches the working test case
        # and correctly routes inference to partner providers when HF Serverless is unsupported.
        self.client = AsyncInferenceClient(provider="auto", token=settings.HF_TOKEN)

    async def generate(self, model: str, prompt: str, system_prompt: str = "", **kwargs) -> Dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 1024),
            temperature=kwargs.get("temperature", 0.7)
        )
        
        answer = response.choices[0].message.content
        usage_info = response.usage
        
        return {
            "answer": answer.strip() if answer else "",
            "usage": {
                "input_tokens": usage_info.prompt_tokens if usage_info else 0,
                "output_tokens": usage_info.completion_tokens if usage_info else 0,
                "total_tokens": usage_info.total_tokens if usage_info else 0
            }
        }

    async def health_check(self, model: str) -> bool:
        try:
            await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1
            )
            return True
        except Exception:
            return False

huggingface_provider = HuggingFaceProvider()
