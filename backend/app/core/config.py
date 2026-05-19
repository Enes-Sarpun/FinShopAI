from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str

    GEMINI_API_KEY: str
    GEMINI_API_KEY_2: str = ""
    GEMINI_API_KEY_3: str = ""
    GEMINI_API_KEY_4: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    SERPAPI_KEY: str = ""

    MANUS_API_KEY: str = ""
    MANUS_API_KEY_2: str = ""
    MANUS_API_KEY_3: str = ""
    MANUS_BASE_URL: str = "https://api.manus.im"
    MANUS_TIMEOUT: int = 60
    MANUS_MAX_RETRIES: int = 2

    ENABLE_MANUS: bool = False
    MANUS_ROLLOUT_PERCENTAGE: int = 0

    OPENAI_API_KEY: str = ""

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"

    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    @property
    def gemini_api_keys(self) -> list[str]:
        """Dolu olan Gemini key'lerini sırayla döner."""
        return [k for k in [self.GEMINI_API_KEY, self.GEMINI_API_KEY_2, self.GEMINI_API_KEY_3, self.GEMINI_API_KEY_4] if k and not k.startswith("YOUR_")]

    @property
    def manus_api_keys(self) -> list[str]:
        """Dolu olan Manus key'lerini sırayla döner."""
        return [k for k in [self.MANUS_API_KEY, self.MANUS_API_KEY_2, self.MANUS_API_KEY_3] if k and not k.startswith("YOUR_")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
