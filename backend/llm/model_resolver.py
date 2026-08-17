from typing import Any, Dict, List

from huggingface_hub import AsyncInferenceClient

from backend.config import settings


class ModelResolver:
    """Resolve configured model IDs against the live Hugging Face catalog.

    Model/provider availability changes independently of the application. The resolver
    therefore treats configured IDs as preferences and selects a live chat-capable
    candidate when a configured model is unavailable.
    """

    def __init__(self) -> None:
        self.client = AsyncInferenceClient(provider="auto", token=settings.HF_TOKEN)
        self._catalog: Dict[str, Dict[str, Any]] | None = None

    async def catalog(self) -> Dict[str, Dict[str, Any]]:
        if self._catalog is not None:
            return self._catalog
        response = await self.client.get("/v1/models")
        data = response.json()
        self._catalog = {item["id"]: item for item in data.get("data", [])}
        return self._catalog

    async def resolve(self, configured_model: str, candidates: List[str]) -> str:
        try:
            catalog = await self.catalog()
        except Exception:
            # Do not block the application if model discovery is temporarily unavailable.
            return configured_model

        preferred = [configured_model] + [m for m in candidates if m != configured_model]
        for model_id in preferred:
            item = catalog.get(model_id)
            if not item:
                continue
            providers = item.get("providers") or []
            live_chat = [
                p for p in providers
                if p.get("status") == "live"
                and p.get("output_modalities", ["text"])
            ]
            if live_chat:
                return model_id
        return configured_model


model_resolver = ModelResolver()
