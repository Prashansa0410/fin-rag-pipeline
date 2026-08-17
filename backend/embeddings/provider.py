from typing import List
from sentence_transformers import SentenceTransformer
from backend.config import settings

class EmbeddingProvider:
    def __init__(self):
        # We use a lightweight model suitable for CPU encoding in demo/portfolio settings
        # In a real environment we might route this through an API
        self.model_name = settings.EMBEDDING_MODEL
        self.model = None

    def _load_model(self):
        if self.model is None:
            # Lazy load the model to save memory if embeddings aren't immediately needed
            self.model = SentenceTransformer(self.model_name)

    def embed_text(self, text: str) -> List[float]:
        self._load_model()
        # Returns a numpy array, convert to list of floats
        embedding = self.model.encode(text)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

embedding_provider = EmbeddingProvider()
