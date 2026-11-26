import pytest
from apps.api.app.core.config import Settings
from pydantic import ValidationError


def _settings(**values: str) -> Settings:
    return Settings(_env_file=None, **values)


def test_postgresql_url_uses_async_driver() -> None:
    settings = _settings(DATABASE_URL="postgresql://user:password@db.example/manutcar")

    assert settings.async_database_url == ("postgresql+asyncpg://user:password@db.example/manutcar")


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="DATABASE_URL"):
        _settings()


def test_legacy_production_environment_names_are_supported() -> None:
    settings = _settings(
        DATABASE_URL="postgresql://user:password@db.example/manutcar",
        APP_ENV="production",
        API_CORS_ORIGINS="https://app.example, https://admin.example",
        CLERK_JWKS_URL="https://clerk.example/.well-known/jwks.json",
        CLERK_JWT_ISSUER="https://clerk.example",
    )

    assert settings.APP_ENV == "production"
    assert settings.cors_origins_list == [
        "https://app.example",
        "https://admin.example",
    ]


def test_canonical_production_environment_names_are_supported() -> None:
    settings = _settings(
        DATABASE_URL="postgresql://user:password@db.example/manutcar",
        ENVIRONMENT="production",
        CORS_ORIGINS='["https://app.example"]',
        CLERK_JWKS_URL="https://clerk.example/.well-known/jwks.json",
        CLERK_JWT_ISSUER="https://clerk.example",
    )

    assert settings.APP_ENV == "production"
    assert settings.cors_origins_list == ["https://app.example"]


def test_production_rejects_sqlite() -> None:
    with pytest.raises(ValidationError, match="SQLite is not supported in production"):
        _settings(
            DATABASE_URL="sqlite+aiosqlite:///:memory:",
            APP_ENV="production",
            API_CORS_ORIGINS="https://app.example",
            CLERK_JWKS_URL="https://clerk.example/.well-known/jwks.json",
            CLERK_JWT_ISSUER="https://clerk.example",
        )


def test_production_requires_clerk_jwks_url() -> None:
    with pytest.raises(ValidationError, match="CLERK_JWKS_URL is required in production"):
        _settings(
            DATABASE_URL="postgresql://user:password@db.example/manutcar",
            APP_ENV="production",
            API_CORS_ORIGINS="https://app.example",
            CLERK_JWT_ISSUER="https://clerk.example",
        )


def test_production_requires_clerk_jwt_issuer() -> None:
    with pytest.raises(ValidationError, match="CLERK_JWT_ISSUER is required in production"):
        _settings(
            DATABASE_URL="postgresql://user:password@db.example/manutcar",
            ENVIRONMENT="production",
            CORS_ORIGINS="https://app.example",
            CLERK_JWKS_URL="https://clerk.example/.well-known/jwks.json",
        )


def test_production_requires_explicit_cors_origins() -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS is required in production"):
        _settings(
            DATABASE_URL="postgresql://user:password@db.example/manutcar",
            ENVIRONMENT="production",
            CLERK_JWKS_URL="https://clerk.example/.well-known/jwks.json",
            CLERK_JWT_ISSUER="https://clerk.example",
        )
