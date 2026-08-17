from abc import ABC, abstractmethod
from typing import Dict, Any, List

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, model: str, prompt: str, system_prompt: str = "", **kwargs) -> Dict[str, Any]:
        """
        Generate text from the LLM provider.
        Returns a dictionary containing the answer and token usage.
        """
        pass

    @abstractmethod
    async def health_check(self, model: str) -> bool:
        """
        Check if the specified model is available on this provider.
        """
        pass
