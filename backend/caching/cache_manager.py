import hashlib
import json
from typing import Dict, Any, Optional

class RetrievalCacheManager:
    def __init__(self):
        # In production this would connect to Redis.
        # For simplicity in this demo, we'll mock the cache store.
        self._cache = {}

    def _generate_key(self, prefix: str, components: Dict[str, Any]) -> str:
        # Sort keys to ensure deterministic hashing
        serialized = json.dumps(components, sort_keys=True)
        hash_val = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        return f"{prefix}:{hash_val}"

    def get_retrieval_cache(self, query: str, filters: Dict[str, Any], document_version_hash: str) -> Optional[Dict[str, Any]]:
        key = self._generate_key("retrieval", {
            "query": query,
            "filters": filters,
            "version_hash": document_version_hash
        })
        return self._cache.get(key)

    def set_retrieval_cache(self, query: str, filters: Dict[str, Any], document_version_hash: str, results: Dict[str, Any]):
        key = self._generate_key("retrieval", {
            "query": query,
            "filters": filters,
            "version_hash": document_version_hash
        })
        self._cache[key] = results
        
    def get_answer_cache(self, retrieval_hash: str, prompt_version: str, model_tier: str) -> Optional[Dict[str, Any]]:
        key = self._generate_key("answer", {
            "retrieval_hash": retrieval_hash,
            "prompt_version": prompt_version,
            "model_tier": model_tier
        })
        return self._cache.get(key)

    def set_answer_cache(self, retrieval_hash: str, prompt_version: str, model_tier: str, answer_data: Dict[str, Any]):
        key = self._generate_key("answer", {
            "retrieval_hash": retrieval_hash,
            "prompt_version": prompt_version,
            "model_tier": model_tier
        })
        self._cache[key] = answer_data

cache_manager = RetrievalCacheManager()
