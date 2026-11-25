import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import AuthContext, get_current_auth_context
from apps.api.app.main import app
from manutcar_db.enums import AgreementStatus, FuelType, OrgRole, VehicleOperationalStatus
from manutcar_db.models.finance_audit import AuditLog
from manutcar_db.models.fleet import Vehicle, VehicleManagementAgreement, VehicleOwner
from manutcar_db.models.identity import Organization, OrganizationMember, User


async def _seed_org_and_vehicle(
    db: AsyncSession,
    org_name: str,
    plate: str,
    odometer: int,
    role: OrgRole = OrgRole.FLEET_MANAGER,
) -> tuple[AuthContext, Vehicle]:
    user = User(
        clerk_user_id=f"user_{uuid.uuid4().hex[:12]}",
        email=f"{uuid.uuid4().hex[:8]}@manutcar.com",
        full_name=f"Actor {org_name}",
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
    owner = VehicleOwner(
        organization_id=org.id,
        owner_type="PJ",
        legal_name=f"Proprietário {org_name}",
        document_number=org.document_number,
    )
    vehicle = Vehicle(
        plate=plate,
        brand="Fiat",
        model="Strada",
        year_manufacture=2023,
        year_model=2024,
        fuel_type=FuelType.GASOLINE,
        current_odometer=odometer,
    )
    db.add_all([member, owner, vehicle])
    await db.flush()

    agreement = VehicleManagementAgreement(
        vehicle_id=vehicle.id,
        organization_id=org.id,
        owner_id=owner.id,
        status=AgreementStatus.ACTIVE,
        start_date=datetime.now(timezone.utc),
    )
    db.add(agreement)
    await db.commit()

    ctx = AuthContext(
        user=user,
        organization=org,
        membership=member,
        clerk_user_id=user.clerk_user_id,
        clerk_org_id=f"org_{uuid.uuid4().hex[:8]}",
    )
    return ctx, vehicle


@pytest.mark.asyncio
async def test_maintenance_preventive_schedule_and_traffic_light(
    ac: AsyncClient,
    db_session: AsyncSession,
):
    ctx, vehicle = await _seed_org_and_vehicle(db_session, "Frota Sul", "MNT1A23", 19500)
    app.dependency_overrides[get_current_auth_context] = lambda: ctx

    try:
        plan_res = await ac.post(
            "/api/v1/maintenance/plans",
            json={"name": "Troca de Óleo", "interval_km": 10000, "interval_days": 180},
        )
        assert plan_res.status_code == 201
        plan_id = plan_res.json()["id"]

        sched_res = await ac.post(
            "/api/v1/maintenance/schedules",
            json={
                "vehicle_id": str(vehicle.id),
                "plan_id": plan_id,
                "last_executed_km": 10000,
                "last_executed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert sched_res.status_code == 201
        body = sched_res.json()
        assert body["next_due_km"] == 20000
        assert body["traffic_light"] == "DUE_SOON"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_work_order_lifecycle_attachment_warranty_rbac_and_isolation(
    ac: AsyncClient,
    db_session: AsyncSession,
):
    mgr_ctx, vehicle = await _seed_org_and_vehicle(db_session, "TransLog", "OSB9X99", 50000)
    other_ctx, _ = await _seed_org_and_vehicle(db_session, "Intrusa SA", "INT0A00", 10000)

    drv_user = User(
        clerk_user_id=f"user_{uuid.uuid4().hex[:12]}",
        email=f"{uuid.uuid4().hex[:8]}@translog.com",
        full_name="Pedro Motorista",
    )
    db_session.add(drv_user)
    await db_session.flush()
    drv_member = OrganizationMember(
        organization_id=mgr_ctx.organization.id,
        user_id=drv_user.id,
        role=OrgRole.DRIVER,
        is_active=True,
    )
    db_session.add(drv_member)
    await db_session.commit()

    drv_ctx = AuthContext(
        user=drv_user,
        organization=mgr_ctx.organization,
        membership=drv_member,
        clerk_user_id=drv_user.clerk_user_id,
        clerk_org_id=mgr_ctx.clerk_org_id,
    )

    try:
        app.dependency_overrides[get_current_auth_context] = lambda: drv_ctx
        req_res = await ac.post(
            "/api/v1/maintenance/requests",
            json={"vehicle_id": str(vehicle.id), "description": "Barulho no freio dianteiro"},
        )
        assert req_res.status_code == 201
        req_id = req_res.json()["id"]

        forbidden_wo = await ac.post(
            "/api/v1/maintenance/work-orders",
            json={
                "vehicle_id": str(vehicle.id),
                "maintenance_type": "CORRECTIVE",
                "odometer_km": 50100,
            },
        )
        assert forbidden_wo.status_code == 403

        app.dependency_overrides[get_current_auth_context] = lambda: mgr_ctx
        prov_res = await ac.post(
            "/api/v1/maintenance/providers",
            json={"name": "Oficina Central", "document_number": "44444444000191"},
        )
        assert prov_res.status_code == 201

        wo_res = await ac.post(
            "/api/v1/maintenance/work-orders",
            json={
                "vehicle_id": str(vehicle.id),
                "service_provider_id": prov_res.json()["id"],
                "request_id": req_id,
                "maintenance_type": "CORRECTIVE",
                "odometer_km": 50200,
                "set_vehicle_in_maintenance": True,
            },
        )
        assert wo_res.status_code == 201
        wo_id = wo_res.json()["id"]

        await db_session.refresh(vehicle)
        assert vehicle.operational_status == VehicleOperationalStatus.MAINTENANCE

        item_res = await ac.post(
            f"/api/v1/maintenance/work-orders/{wo_id}/items",
            json={
                "description": "Jogo Pastilha de Freio",
                "quantity": "1",
                "unit_price": "650.00",
                "warranty_days": 90,
                "warranty_km": 10000,
            },
        )
        assert item_res.status_code == 201
        assert item_res.json()["total_amount"] == "650.00"

        fail_complete = await ac.patch(
            f"/api/v1/maintenance/work-orders/{wo_id}/status",
            json={"status": "COMPLETED", "has_attachments": False},
        )
        assert fail_complete.status_code == 400
        assert fail_complete.json()["detail"]["code"] == "MISSING_ATTACHMENT"

        ok_complete = await ac.patch(
            f"/api/v1/maintenance/work-orders/{wo_id}/status",
            json={"status": "COMPLETED", "has_attachments": True},
        )
        assert ok_complete.status_code == 200
        assert ok_complete.json()["status"] == "COMPLETED"

        await db_session.refresh(vehicle)
        assert vehicle.operational_status == VehicleOperationalStatus.ACTIVE

        wo2_res = await ac.post(
            "/api/v1/maintenance/work-orders",
            json={
                "vehicle_id": str(vehicle.id),
                "maintenance_type": "CORRECTIVE",
                "odometer_km": 51000,
            },
        )
        wo2_id = wo2_res.json()["id"]

        warranty_block = await ac.post(
            f"/api/v1/maintenance/work-orders/{wo2_id}/items",
            json={
                "description": "Jogo Pastilha de Freio",
                "quantity": "1",
                "unit_price": "650.00",
            },
        )
        assert warranty_block.status_code == 409
        assert warranty_block.json()["detail"]["code"] == "WARRANTY_COVERAGE_DETECTED"

        app.dependency_overrides[get_current_auth_context] = lambda: other_ctx
        iso_res = await ac.get("/api/v1/maintenance/work-orders")
        assert iso_res.status_code == 200
        assert iso_res.json() == []

        audits = (
            await db_session.scalars(
                select(AuditLog).where(
                    AuditLog.organization_id == mgr_ctx.organization.id,
                    AuditLog.entity_name.in_(["WorkOrder", "WorkOrderItem", "MaintenanceRequest"]),
                )
            )
        ).all()
        assert len(audits) >= 4
    finally:
        app.dependency_overrides.clear()
