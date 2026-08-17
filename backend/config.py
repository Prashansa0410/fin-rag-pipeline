from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HF_TOKEN: str = ""

    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/finresearch"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Model IDs are configuration, not routing logic. They can be overridden
    # safely through .env / deployment secrets as Hugging Face availability changes.
    ECONOMICAL_MODEL: str = "Qwen/Qwen2.5-1.5B-Instruct"
    STANDARD_MODEL: str = "mistralai/Mistral-Nemo-Instruct-2407"
    ADVANCED_MODEL: str = "Qwen/Qwen2.5-72B-Instruct"
    FALLBACK_MODEL: str = "Qwen/Qwen2.5-1.5B-Instruct"

    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    MODEL_ROUTING_ENABLED: bool = True
    CACHE_ENABLED: bool = True

    MAX_UPLOAD_SIZE: int = 10485760  # 10MB

    RESPONSE_TOKEN_RESERVE: int = 2000
    TOKEN_SAFETY_MARGIN: int = 500

    RATE_LIMIT: str = "30/minute"

    VECTOR_WEIGHT: float = 0.7
    KEYWORD_WEIGHT: float = 0.3
    METADATA_BOOST: float = 0.2

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
