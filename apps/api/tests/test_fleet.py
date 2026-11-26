import uuid
from datetime import datetime, timezone

import pytest
from apps.api.app.core.security import (
    AuthContext,
    get_current_auth_context,
    verify_vehicle_access,
)
from apps.api.app.main import app
from apps.api.app.services.maintenance_service import _ensure_vehicle_access
from apps.api.app.services.operations_service import _assert_vehicle_in_org
from fastapi import HTTPException
from httpx import AsyncClient
from manutcar_db.enums import AgreementStatus, OrgRole
from manutcar_db.models.finance_audit import AuditLog
from manutcar_db.models.fleet import VehicleManagementAgreement
from manutcar_db.models.identity import Organization, OrganizationMember, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


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

    agreements = (await ac.get("/api/v1/fleet/agreements", params={"vehicle_id": veh_id})).json()
    assert agreements
    assert all(agreement["status"] == AgreementStatus.ACTIVE.value for agreement in agreements)

    # AuditLog imutavel registrado para todas as mutacoes da Org Gama
    logs = list((await db_session.scalars(
        select(AuditLog).where(AuditLog.organization_id == actor_mgr.organization.id)
    )).all())
    assert len(logs) >= 5


async def _create_vehicle_for_owner(ac: AsyncClient, owner_id: str, plate: str) -> str:
    response = await ac.post(
        "/api/v1/fleet/vehicles",
        json={
            "plate": plate,
            "brand": "Volvo",
            "model": "FH 540",
            "year_manufacture": 2023,
            "year_model": 2024,
            "fuel_type": "DIESEL",
            "current_owner_id": owner_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.asyncio
async def test_cross_org_agreement_remains_blocked_until_scopes_are_defined(
    ac: AsyncClient, db_session: AsyncSession
):
    owner_admin = await _seed_actor(
        db_session, "Owner Org", "owner-org", "admin@owner.test", OrgRole.ADMIN
    )
    manager = await _seed_actor(db_session, "Manager Org", "manager-org", "manager@test.test")

    _use_actor(owner_admin)
    owner = await ac.post(
        "/api/v1/fleet/owners",
        json={
            "owner_type": "PJ",
            "legal_name": "Owner Org Ltda",
            "document_number": "12345678000199",
        },
    )
    assert owner.status_code == 201, owner.text
    vehicle_id = await _create_vehicle_for_owner(ac, owner.json()["id"], "ABC1D23")

    _use_actor(manager)
    created = await ac.post(
        "/api/v1/fleet/agreements",
        json={
            "vehicle_id": vehicle_id,
            "owner_id": owner.json()["id"],
            "start_date": "2025-01-01T00:00:00Z",
        },
    )
    assert created.status_code == 201, created.text
    agreement = created.json()
    agreement_id = agreement["id"]
    assert agreement["status"] == AgreementStatus.PENDING.value
    assert agreement["consented_by_user_id"] is None
    assert agreement["consented_at"] is None

    forced_activation = await ac.patch(
        f"/api/v1/fleet/agreements/{agreement_id}/status",
        json={"status": AgreementStatus.ACTIVE.value},
    )
    assert forced_activation.status_code == 409
    assert (await ac.post(f"/api/v1/fleet/agreements/{agreement_id}/consent")).status_code == 403

    non_admin_user = User(
        clerk_user_id=f"user_{uuid.uuid4().hex[:12]}",
        email="fleet-manager@owner.test",
        full_name="Owner Org Fleet Manager",
    )
    db_session.add(non_admin_user)
    await db_session.flush()
    non_admin_member = OrganizationMember(
        organization_id=owner_admin.organization.id,
        user_id=non_admin_user.id,
        role=OrgRole.FLEET_MANAGER,
        is_active=True,
    )
    db_session.add(non_admin_member)
    await db_session.commit()
    non_admin = AuthContext(
        user=non_admin_user,
        organization=owner_admin.organization,
        membership=non_admin_member,
        clerk_user_id=non_admin_user.clerk_user_id,
        clerk_org_id=owner_admin.clerk_org_id,
    )
    _use_actor(non_admin)
    assert (await ac.post(f"/api/v1/fleet/agreements/{agreement_id}/consent")).status_code == 403

    _use_actor(owner_admin)
    pending = await ac.get("/api/v1/fleet/agreements/pending-consent")
    assert [item["id"] for item in pending.json()] == [agreement_id]

    blocked = await ac.post(f"/api/v1/fleet/agreements/{agreement_id}/consent")
    assert blocked.status_code == 409
    assert "escopos granulares" in blocked.json()["detail"]

    refused = await ac.delete(f"/api/v1/fleet/agreements/{agreement_id}/consent")
    assert refused.status_code == 200, refused.text
    assert refused.json()["status"] == AgreementStatus.REVOKED.value
    assert refused.json()["consent_revoked_at"] is None
    stored = await db_session.get(VehicleManagementAgreement, uuid.UUID(agreement_id))
    assert stored is not None
    assert stored.status == AgreementStatus.REVOKED
    assert stored.consented_at is None


@pytest.mark.asyncio
async def test_cross_org_pf_consent_is_blocked_until_scopes_are_defined(
    ac: AsyncClient, db_session: AsyncSession
):
    owner_user = await _seed_actor(
        db_session, "Personal Owner Org", "personal-owner-org", "person@test.test"
    )
    manager = await _seed_actor(
        db_session, "Fleet Manager Org", "fleet-manager-org", "fleetmanager@test.test"
    )

    _use_actor(owner_user)
    owner = await ac.post(
        "/api/v1/fleet/owners",
        json={
            "owner_type": "PF",
            "legal_name": "Pessoa Proprietaria",
            "document_number": "12345678901",
            "user_id": str(owner_user.user.id),
        },
    )
    assert owner.status_code == 201, owner.text
    vehicle_id = await _create_vehicle_for_owner(ac, owner.json()["id"], "XYZ9Z88")

    _use_actor(manager)
    created = await ac.post(
        "/api/v1/fleet/agreements",
        json={
            "vehicle_id": vehicle_id,
            "owner_id": owner.json()["id"],
            "start_date": "2025-01-01T00:00:00Z",
        },
    )
    assert created.status_code == 201, created.text
    agreement_id = created.json()["id"]

    assert (await ac.post(f"/api/v1/fleet/agreements/{agreement_id}/consent")).status_code == 403

    _use_actor(owner_user)
    blocked = await ac.post(f"/api/v1/fleet/agreements/{agreement_id}/consent")
    assert blocked.status_code == 409
    assert "escopos granulares" in blocked.json()["detail"]
    stored = await db_session.get(VehicleManagementAgreement, uuid.UUID(agreement_id))
    assert stored is not None
    assert stored.status == AgreementStatus.PENDING
    assert stored.consented_at is None


@pytest.mark.asyncio
async def test_legacy_active_cross_org_agreement_does_not_grant_access(
    ac: AsyncClient, db_session: AsyncSession
):
    owner_org = await _seed_actor(
        db_session, "Legacy Owner Org", "legacy-owner", "owner@legacy.test", OrgRole.ADMIN
    )
    manager = await _seed_actor(
        db_session, "Legacy Manager Org", "legacy-manager", "manager@legacy.test"
    )

    _use_actor(owner_org)
    owner = await ac.post(
        "/api/v1/fleet/owners",
        json={
            "owner_type": "PJ",
            "legal_name": "Legacy Owner Ltda",
            "document_number": "22222222000122",
        },
    )
    assert owner.status_code == 201, owner.text
    vehicle_id = await _create_vehicle_for_owner(ac, owner.json()["id"], "QRS1T23")

    legacy_agreement = VehicleManagementAgreement(
        vehicle_id=uuid.UUID(vehicle_id),
        organization_id=manager.organization.id,
        owner_id=uuid.UUID(owner.json()["id"]),
        status=AgreementStatus.ACTIVE,
        start_date=datetime.now(timezone.utc),
    )
    db_session.add(legacy_agreement)
    await db_session.commit()

    _use_actor(manager)
    assert (await ac.get("/api/v1/fleet/vehicles")).json() == []
    assert (await ac.get(f"/api/v1/fleet/vehicles/{vehicle_id}")).status_code == 404

    with pytest.raises(HTTPException) as security_error:
        await verify_vehicle_access(db_session, manager, uuid.UUID(vehicle_id))
    assert security_error.value.status_code == 403

    with pytest.raises(HTTPException) as maintenance_error:
        await _ensure_vehicle_access(db_session, manager.organization.id, uuid.UUID(vehicle_id))
    assert maintenance_error.value.status_code == 403

    with pytest.raises(HTTPException) as operations_error:
        await _assert_vehicle_in_org(db_session, manager.organization.id, uuid.UUID(vehicle_id))
    assert operations_error.value.status_code == 404


@pytest.mark.asyncio
async def test_transfer_revokes_pending_cross_org_agreement(
    ac: AsyncClient, db_session: AsyncSession
):
    owner_admin = await _seed_actor(
        db_session,
        "Transfer Owner Org",
        "transfer-owner",
        "admin@transfer-owner.test",
        OrgRole.ADMIN,
    )
    manager = await _seed_actor(
        db_session, "Transfer Manager Org", "transfer-manager", "manager@transfer.test"
    )

    _use_actor(owner_admin)
    owner = await ac.post(
        "/api/v1/fleet/owners",
        json={
            "owner_type": "PJ",
            "legal_name": "Transfer Owner Ltda",
            "document_number": "98765432000199",
        },
    )
    assert owner.status_code == 201, owner.text
    vehicle_id = await _create_vehicle_for_owner(ac, owner.json()["id"], "KLM1N23")

    _use_actor(manager)
    created = await ac.post(
        "/api/v1/fleet/agreements",
        json={
            "vehicle_id": vehicle_id,
            "owner_id": owner.json()["id"],
            "start_date": "2025-01-01T00:00:00Z",
        },
    )
    assert created.status_code == 201, created.text
    agreement_id = created.json()["id"]
    assert created.json()["status"] == AgreementStatus.PENDING.value

    _use_actor(owner_admin)
    new_owner = await ac.post(
        "/api/v1/fleet/owners",
        json={
            "owner_type": "PJ",
            "legal_name": "New Transfer Owner Ltda",
            "document_number": "11111111000191",
        },
    )
    assert new_owner.status_code == 201, new_owner.text
    transfer = await ac.post(
        f"/api/v1/fleet/vehicles/{vehicle_id}/transfer-ownership",
        json={"new_owner_id": new_owner.json()["id"]},
    )
    assert transfer.status_code == 200, transfer.text

    stored = await db_session.get(VehicleManagementAgreement, uuid.UUID(agreement_id))
    assert stored is not None
    assert stored.status == AgreementStatus.REVOKED
