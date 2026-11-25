import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import AuthContext, get_current_auth_context
from apps.api.app.main import app
from manutcar_db.enums import OrgRole
from manutcar_db.models.finance_audit import AuditLog
from manutcar_db.models.identity import Organization, OrganizationMember, User


async def _seed_actor(
    db: AsyncSession,
    org_name: str,
    slug: str,
    email: str,
    role: OrgRole = OrgRole.FLEET_MANAGER,
) -> AuthContext:
    user = User(
        clerk_user_id=f"user_{uuid.uuid4().hex[:12]}",
        email=email,
        full_name=f"User {org_name}",
    )
    org = Organization(
        name=org_name,
        document_number=f"{uuid.uuid4().int % 10**14:014d}",
        is_personal_workspace=False,
    )
    db.add_all([user, org])
    await db.flush()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=role,
        is_active=True,
    )
    db.add(member)
    await db.commit()
    return AuthContext(
        user=user,
        organization=org,
        membership=member,
        clerk_user_id=user.clerk_user_id,
        clerk_org_id=f"org_{slug}_{uuid.uuid4().hex[:8]}",
    )


def _use_actor(actor: AuthContext) -> None:
    async def _override():
        return actor

    app.dependency_overrides[get_current_auth_context] = _override


@pytest.mark.asyncio
async def test_fleet_crud_and_multitenant_isolation(ac: AsyncClient, db_session: AsyncSession):
    actor_a = await _seed_actor(db_session, "Org Alpha", "org-alpha", "alpha@manutcar.test")
    actor_b = await _seed_actor(db_session, "Org Beta", "org-beta", "beta@manutcar.test")

    # 1. Org A cria proprietario PJ
    _use_actor(actor_a)
    res_owner = await ac.post(
        "/api/v1/fleet/owners",
        json={
            "owner_type": "PJ",
            "legal_name": "Transportes Alpha Ltda",
            "document_number": "12.345.678/0001-99",
        },
    )
    assert res_owner.status_code == 201, res_owner.text
    owner_id = res_owner.json()["id"]

    # 2. Org A cria veiculo (gera historico de posse + acordo ativo)
    res_veh = await ac.post(
        "/api/v1/fleet/vehicles",
        json={
            "plate": "ABC-1D23",
            "brand": "Volvo",
            "model": "FH 540",
            "year_manufacture": 2023,
            "year_model": 2024,
            "fuel_type": "DIESEL",
            "current_odometer": 15000,
            "current_owner_id": owner_id,
        },
    )
    assert res_veh.status_code == 201, res_veh.text
    veh = res_veh.json()
    assert veh["plate"] == "ABC1D23"
    veh_id = veh["id"]

    # 3. Isolamento Multi-Tenant (RN-FLT-01): Org B nao enxerga veiculo nem proprietario da Org A
    _use_actor(actor_b)
    assert (await ac.get("/api/v1/fleet/vehicles")).json() == []
    assert (await ac.get(f"/api/v1/fleet/vehicles/{veh_id}")).status_code == 404
    assert (await ac.get(f"/api/v1/fleet/owners/{owner_id}")).status_code == 404


@pytest.mark.asyncio
async def test_odometer_monotonic_transfer_rbac_and_audit_log(ac: AsyncClient, db_session: AsyncSession):
    actor_mgr = await _seed_actor(db_session, "Org Gama", "org-gama", "mgr@gama.test", OrgRole.FLEET_MANAGER)
    actor_drv = await _seed_actor(db_session, "Org Gama Driver", "org-gama-drv", "drv@gama.test", OrgRole.DRIVER)

    # RBAC: DRIVER nao pode cadastrar proprietario (403)
    _use_actor(actor_drv)
    res_forbidden = await ac.post(
        "/api/v1/fleet/owners",
        json={"owner_type": "PF", "legal_name": "Motorista Teste", "document_number": "12345678901"},
    )
    assert res_forbidden.status_code == 403

    # FLEET_MANAGER cria dois proprietarios e um veiculo
    _use_actor(actor_mgr)
    o1 = (await ac.post(
        "/api/v1/fleet/owners",
        json={"owner_type": "PF", "legal_name": "Joao Silva", "document_number": "11122233344"},
    )).json()
    o2 = (await ac.post(
        "/api/v1/fleet/owners",
        json={"owner_type": "PF", "legal_name": "Maria Souza", "document_number": "55566677788"},
    )).json()

    veh = (await ac.post(
        "/api/v1/fleet/vehicles",
        json={
            "plate": "XYZ9876",
            "brand": "Scania",
            "model": "R 450",
            "year_manufacture": 2022,
            "year_model": 2022,
            "fuel_type": "DIESEL",
            "current_odometer": 50000,
            "current_owner_id": o1["id"],
        },
    )).json()
    veh_id = veh["id"]

    # Odometro monotonico: regressao (49999) bloqueada com 422
    res_bad_odo = await ac.patch(f"/api/v1/fleet/vehicles/{veh_id}/odometer", json={"new_odometer": 49999})
    assert res_bad_odo.status_code == 422

    # Odometro monotonico: avanco (51200) permitido
    res_ok_odo = await ac.patch(
        f"/api/v1/fleet/vehicles/{veh_id}/odometer",
        json={"new_odometer": 51200, "reason": "Check-in oficina"},
    )
    assert res_ok_odo.status_code == 200
    assert res_ok_odo.json()["current_odometer"] == 51200

    # Transferencia de propriedade fecha historico anterior e abre novo
    res_tr = await ac.post(
        f"/api/v1/fleet/vehicles/{veh_id}/transfer-ownership",
        json={"new_owner_id": o2["id"], "reason": "Venda interna"},
    )
    assert res_tr.status_code == 200
    assert res_tr.json()["current_owner_id"] == o2["id"]

    hist = (await ac.get(f"/api/v1/fleet/vehicles/{veh_id}/ownership-history")).json()
    assert len(hist) == 2

    # AuditLog imutavel registrado para todas as mutacoes da Org Gama
    logs = list((await db_session.scalars(
        select(AuditLog).where(AuditLog.organization_id == actor_mgr.organization.id)
    )).all())
    assert len(logs) >= 5
