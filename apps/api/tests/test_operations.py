import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import AuthContext, get_current_auth_context
from apps.api.app.main import app
from manutcar_db.enums import OrgRole
from manutcar_db.models.finance_audit import AuditLog
from manutcar_db.models.identity import Organization, OrganizationMember, User


async def _seed_org_and_actor(
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


async def _add_member(
    db: AsyncSession,
    org: Organization,
    email: str,
    role: OrgRole,
) -> AuthContext:
    user = User(
        clerk_user_id=f"user_{uuid.uuid4().hex[:12]}",
        email=email,
        full_name=f"Member {role.value}",
    )
    db.add(user)
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
        clerk_org_id=f"org_{org.id.hex[:8]}",
    )


def _use_actor(actor: AuthContext) -> None:
    async def _override():
        return actor

    app.dependency_overrides[get_current_auth_context] = _override


async def _create_vehicle_for_actor(ac: AsyncClient, plate: str) -> str:
    owner = (
        await ac.post(
            "/api/v1/fleet/owners",
            json={
                "owner_type": "PJ",
                "legal_name": f"Owner {plate}",
                "document_number": f"{uuid.uuid4().int % 10**14:014d}",
            },
        )
    ).json()
    veh = (
        await ac.post(
            "/api/v1/fleet/vehicles",
            json={
                "plate": plate,
                "brand": "Mercedes-Benz",
                "model": "Accelo 1016",
                "year_manufacture": 2023,
                "year_model": 2023,
                "fuel_type": "DIESEL",
                "current_odometer": 10000,
                "current_owner_id": owner["id"],
            },
        )
    ).json()
    return veh["id"]


@pytest.mark.asyncio
async def test_assignments_shifts_overlap_rbac_and_isolation(
    ac: AsyncClient, db_session: AsyncSession
):
    mgr = await _seed_org_and_actor(db_session, "Ops Org A", "ops-a", "mgr@opsa.test")
    drv1 = await _add_member(db_session, mgr.organization, "drv1@opsa.test", OrgRole.DRIVER)
    drv2 = await _add_member(db_session, mgr.organization, "drv2@opsa.test", OrgRole.DRIVER)
    maint = await _add_member(db_session, mgr.organization, "mnt@opsa.test", OrgRole.MAINTENANCE)
    other_org_mgr = await _seed_org_and_actor(db_session, "Ops Org B", "ops-b", "mgr@opsb.test")

    _use_actor(mgr)
    veh_id = await _create_vehicle_for_actor(ac, "OPS1A23")

    t0 = datetime(2026, 5, 10, 8, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 5, 10, 16, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 5, 10, 23, 0, tzinfo=timezone.utc)

    # 1. Aloca Motorista 1 no turno da manhã (08:00 - 16:00)
    res1 = await ac.post(
        "/api/v1/operations/assignments",
        json={
            "vehicle_id": veh_id,
            "driver_user_id": str(drv1.user.id),
            "start_datetime": t0.isoformat(),
            "end_datetime": t1.isoformat(),
            "shift_label": "Manhã",
        },
    )
    assert res1.status_code == 201, res1.text
    a1_id = res1.json()["id"]

    # 2. RN-FLT-06: Sobreposição para o mesmo Motorista 1 (14:00 - 20:00) bloqueada (409)
    res_overlap = await ac.post(
        "/api/v1/operations/assignments",
        json={
            "vehicle_id": veh_id,
            "driver_user_id": str(drv1.user.id),
            "start_datetime": (t0 + timedelta(hours=6)).isoformat(),
            "end_datetime": (t1 + timedelta(hours=4)).isoformat(),
            "shift_label": "Conflito",
        },
    )
    assert res_overlap.status_code == 409

    # 3. RN-FLT-06: Múltiplos motoristas no mesmo veículo em turnos distintos (Motorista 2 em aberto)
    res2 = await ac.post(
        "/api/v1/operations/assignments",
        json={
            "vehicle_id": veh_id,
            "driver_user_id": str(drv2.user.id),
            "start_datetime": t1.isoformat(),
            "shift_label": "Noite",
        },
    )
    assert res2.status_code == 201, res2.text
    a2_id = res2.json()["id"]

    # 4. RBAC: DRIVER enxerga apenas a própria alocação e não pode criar (403)
    _use_actor(drv1)
    assert (await ac.post("/api/v1/operations/assignments", json={})).status_code in (403, 422)
    drv1_list = (await ac.get("/api/v1/operations/assignments")).json()
    assert len(drv1_list) == 1
    assert drv1_list[0]["id"] == a1_id
    assert (await ac.get(f"/api/v1/operations/assignments/{a2_id}")).status_code == 404

    # 5. RBAC: MAINTENANCE não acessa alocações (403)
    _use_actor(maint)
    assert (await ac.get("/api/v1/operations/assignments")).status_code == 403

    # 6. Isolamento Multi-Tenant: Org B não enxerga alocações da Org A
    _use_actor(other_org_mgr)
    assert (await ac.get("/api/v1/operations/assignments")).json() == []
    assert (await ac.get(f"/api/v1/operations/assignments/{a1_id}")).status_code == 404

    # 7. Encerramento de turno em aberto (close) e AuditLog
    _use_actor(mgr)
    res_close = await ac.post(
        f"/api/v1/operations/assignments/{a2_id}/close",
        json={"end_datetime": t2.isoformat()},
    )
    assert res_close.status_code == 200
    assert res_close.json()["end_datetime"] is not None

    logs = list(
        (
            await db_session.scalars(
                select(AuditLog).where(
                    AuditLog.organization_id == mgr.organization.id,
                    AuditLog.entity_name == "VehicleAssignment",
                )
            )
        ).all()
    )
    assert len(logs) == 3  # 2 CREATE + 1 UPDATE (close)


@pytest.mark.asyncio
async def test_financial_responsibilities_upsert_rbac_and_audit(
    ac: AsyncClient, db_session: AsyncSession
):
    mgr = await _seed_org_and_actor(db_session, "Fin Org", "fin-org", "mgr@finorg.test")
    fin = await _add_member(db_session, mgr.organization, "fin@finorg.test", OrgRole.FINANCIAL)
    drv = await _add_member(db_session, mgr.organization, "drv@finorg.test", OrgRole.DRIVER)

    _use_actor(mgr)
    veh_id = await _create_vehicle_for_actor(ac, "FIN9B88")

    # 1. FINANCIAL cria regra de responsabilidade para FUEL
    _use_actor(fin)
    res_create = await ac.put(
        "/api/v1/operations/financial-responsibilities",
        json={
            "vehicle_id": veh_id,
            "expense_category": "fuel",
            "default_payer_type": "DRIVER",
            "default_economic_owner_type": "DRIVER",
        },
    )
    assert res_create.status_code == 200, res_create.text
    rule = res_create.json()
    assert rule["expense_category"] == "FUEL"
    assert rule["default_payer_type"] == "DRIVER"

    # 2. Upsert atualiza a mesma categoria (ORG paga, DRIVER é dono econômico -> reembolso futuro)
    res_update = await ac.put(
        "/api/v1/operations/financial-responsibilities",
        json={
            "vehicle_id": veh_id,
            "expense_category": "FUEL",
            "default_payer_type": "ORG",
            "default_economic_owner_type": "DRIVER",
        },
    )
    assert res_update.status_code == 200
    assert res_update.json()["id"] == rule["id"]
    assert res_update.json()["default_payer_type"] == "ORG"

    # 3. RBAC: DRIVER não pode ler nem alterar responsabilidades financeiras (403)
    _use_actor(drv)
    assert (
        await ac.get("/api/v1/operations/financial-responsibilities", params={"vehicle_id": veh_id})
    ).status_code == 403

    # 4. Listagem e exclusão pelo gestor + validação AuditLog
    _use_actor(mgr)
    rules_list = (
        await ac.get("/api/v1/operations/financial-responsibilities", params={"vehicle_id": veh_id})
    ).json()
    assert len(rules_list) == 1

    res_del = await ac.delete(f"/api/v1/operations/financial-responsibilities/{rule['id']}")
    assert res_del.status_code == 204

    logs = list(
        (
            await db_session.scalars(
                select(AuditLog).where(
                    AuditLog.organization_id == mgr.organization.id,
                    AuditLog.entity_name == "VehicleFinancialResponsibility",
                )
            )
        ).all()
    )
    assert len(logs) == 3  # CREATE + UPDATE + DELETE
