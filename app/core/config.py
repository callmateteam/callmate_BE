from pydantic_settings import BaseSettings
from pydantic import SecretStr
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings (MVP)"""

    # Application
    APP_NAME: str = "CallMate API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # OpenAI (필수 - 통화 분석)
    OPENAI_API_KEY: SecretStr

    # Deepgram (필수 - 음성→텍스트, 빠른 처리)
    DEEPGRAM_API_KEY: SecretStr

    # CORS (Vercel 프론트엔드)
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # File Upload
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    UPLOAD_DIR: str = "./uploads"

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
