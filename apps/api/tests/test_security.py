import time
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from apps.api.app.core import security
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException


@pytest.fixture
def token_builder(monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[str, Any] | None], str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwks_url = "https://clerk.example/.well-known/jwks.json"

    class FakeJWKClient:
        def __init__(self, uri: str) -> None:
            assert uri == jwks_url

        def get_signing_key_from_jwt(self, token: str) -> SimpleNamespace:
            return SimpleNamespace(key=private_key.public_key())

    monkeypatch.setattr(security, "PyJWKClient", FakeJWKClient)
    monkeypatch.setattr(security.settings, "CLERK_JWKS_URL", jwks_url)
    monkeypatch.setattr(security.settings, "CLERK_JWT_ISSUER", "https://clerk.example")
    monkeypatch.setattr(security.settings, "CLERK_JWT_AUDIENCE", "")

    def build_token(extra_claims: dict[str, Any] | None = None) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {
            "iss": "https://clerk.example",
            "sub": "user_test",
            "iat": now,
            "exp": now + 300,
        }
        claims.update(extra_claims or {})
        return jwt.encode(claims, private_key, algorithm="RS256")

    return build_token


def test_decode_accepts_valid_token_from_configured_issuer(
    token_builder: Callable[[dict[str, Any] | None], str],
) -> None:
    payload = security.decode_clerk_jwt(token_builder(None))

    assert payload["sub"] == "user_test"


def test_decode_rejects_wrong_issuer(
    token_builder: Callable[[dict[str, Any] | None], str],
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        security.decode_clerk_jwt(token_builder({"iss": "https://attacker.example"}))

    assert exc_info.value.status_code == 401


def test_decode_rejects_malformed_expiration_claim(
    token_builder: Callable[[dict[str, Any] | None], str],
) -> None:
    token = token_builder({"exp": None})

    with pytest.raises(HTTPException) as exc_info:
        security.decode_clerk_jwt(token)

    assert exc_info.value.status_code == 401


def test_decode_validates_configured_audience(
    monkeypatch: pytest.MonkeyPatch,
    token_builder: Callable[[dict[str, Any] | None], str],
) -> None:
    monkeypatch.setattr(security.settings, "CLERK_JWT_AUDIENCE", "api://manutcar")
    token = token_builder({"aud": "api://other"})

    with pytest.raises(HTTPException) as exc_info:
        security.decode_clerk_jwt(token)

    assert exc_info.value.status_code == 401


def test_decode_rejects_unconfigured_audience(
    token_builder: Callable[[dict[str, Any] | None], str],
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        security.decode_clerk_jwt(token_builder({"aud": "api://manutcar"}))

    assert exc_info.value.status_code == 401
