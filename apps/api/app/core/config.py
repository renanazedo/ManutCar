import json

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    DATABASE_URL: str
    CLERK_SECRET_KEY: str = ""
    CLERK_WEBHOOK_SECRET: str = ""
    CLERK_JWKS_URL: str = ""
    CLERK_JWT_ISSUER: str = ""
    CLERK_JWT_AUDIENCE: str = ""
    CORS_ORIGINS: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CORS_ORIGINS", "API_CORS_ORIGINS"),
    )
    ENVIRONMENT: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"),
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        try:
            url = make_url(value)
        except ArgumentError as exc:
            raise ValueError("DATABASE_URL must be a valid SQLAlchemy URL") from exc

        if url.drivername not in {
            "postgresql",
            "postgresql+asyncpg",
            "sqlite+aiosqlite",
        }:
            raise ValueError(
                "DATABASE_URL must use postgresql, postgresql+asyncpg, or sqlite+aiosqlite"
            )
        return value

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.APP_ENV.lower() == "production":
            if make_url(self.DATABASE_URL).drivername.startswith("sqlite"):
                raise ValueError("SQLite is not supported in production")
            if not self.CLERK_JWKS_URL.strip():
                raise ValueError("CLERK_JWKS_URL is required in production")
            if not self.CLERK_JWT_ISSUER.strip():
                raise ValueError("CLERK_JWT_ISSUER is required in production")
            if not self.CORS_ORIGINS or not self.cors_origins_list:
                raise ValueError("CORS_ORIGINS is required in production")
        return self

    @property
    def APP_ENV(self) -> str:
        return self.ENVIRONMENT

    @property
    def cors_origins_list(self) -> list[str]:
        origins = self.CORS_ORIGINS or "http://localhost:3000"
        if origins.lstrip().startswith("["):
            try:
                parsed_origins = json.loads(origins)
            except json.JSONDecodeError as exc:
                raise ValueError("CORS_ORIGINS must be comma-separated or a JSON array") from exc
            if not isinstance(parsed_origins, list) or not all(
                isinstance(origin, str) for origin in parsed_origins
            ):
                raise ValueError("CORS_ORIGINS JSON value must be an array of strings")
            return [origin.strip() for origin in parsed_origins if origin.strip()]
        return [origin.strip() for origin in origins.split(",") if origin.strip()]

    @property
    def async_database_url(self) -> str:
        url = make_url(self.DATABASE_URL)
        if url.drivername == "postgresql":
            url = url.set(drivername="postgresql+asyncpg")
        return url.render_as_string(hide_password=False)


settings = Settings()
