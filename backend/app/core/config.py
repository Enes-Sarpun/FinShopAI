from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str

    # Gemini
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # SerpAPI
    SERPAPI_KEY: str = ""

    # Manus API
    MANUS_API_KEY: str = ""
    MANUS_BASE_URL: str = "https://api.manus.im"
    MANUS_TIMEOUT: int = 60
    MANUS_MAX_RETRIES: int = 2

    # LLM Routing
    ENABLE_MANUS: bool = False
    MANUS_ROLLOUT_PERCENTAGE: int = 0

    # OpenAI (backup)
    OPENAI_API_KEY: str = ""

    # App
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
