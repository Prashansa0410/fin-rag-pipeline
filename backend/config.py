from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HF_TOKEN: str = ""

    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/finresearch"
    REDIS_URL: str = "redis://localhost:6379/0"

    # General-purpose instruction models with current Hugging Face Inference Provider support.
    # Keep these configurable because provider/model availability can change.
    ECONOMICAL_MODEL: str = "meta-llama/Llama-3.2-3B-Instruct"
    STANDARD_MODEL: str = "Qwen/Qwen3-4B-Instruct-2507"
    ADVANCED_MODEL: str = "Qwen/Qwen2.5-72B-Instruct"
    FALLBACK_MODEL: str = "meta-llama/Llama-3.2-3B-Instruct"

    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    MODEL_ROUTING_ENABLED: bool = True
    CACHE_ENABLED: bool = True

    MAX_UPLOAD_SIZE: int = 10485760  # 10MB

    RESPONSE_TOKEN_RESERVE: int = 2000
    TOKEN_SAFETY_MARGIN: int = 500

    RATE_LIMIT: str = "30/minute"

    VECTOR_WEIGHT: float = 0.60
    KEYWORD_WEIGHT: float = 0.25
    LEXICAL_WEIGHT: float = 0.15
    METADATA_BOOST: float = 0.2

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
