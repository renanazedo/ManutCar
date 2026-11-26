from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_health_reports_api_and_database_status(ac: AsyncClient):
    response = await ac.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"


@pytest.mark.asyncio
async def test_health_reports_database_unavailable(
    ac: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        db_session,
        "execute",
        AsyncMock(side_effect=SQLAlchemyError("database unavailable")),
    )

    response = await ac.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"
