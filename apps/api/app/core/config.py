from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_ENV: str = "development"
    APP_TZ: str = "America/Sao_Paulo"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = Field(..., min_length=32)

    DATABASE_URL: str
    DATABASE_URL_UNPOOLED: Optional[str] = None

    CLERK_SECRET_KEY: str
    CLERK_WEBHOOK_SECRET: str
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: str

    API_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.API_CORS_ORIGINS.split(",") if origin.strip()]

    R2_ACCOUNT_ID: str
    R2_ACCESS_KEY_ID: str
    R2_SECRET_ACCESS_KEY: str
    R2_BUCKET_NAME: str
    R2_PUBLIC_URL: Optional[str] = None

    RESEND_API_KEY: str
    EMAIL_FROM: str = "ManutCar <onboarding@resend.dev>"

    FCM_SERVICE_ACCOUNT_JSON_BASE64: Optional[str] = None

    NEXT_PUBLIC_APP_URL: str = "http://localhost:3000"
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
