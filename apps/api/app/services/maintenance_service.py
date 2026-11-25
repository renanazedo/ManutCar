from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.app.services.audit import record_audit_log
from manutcar.schemas.maintenance import (
    MaintenancePlanCreate,
    MaintenanceRequestCreate,
    PreventiveTrafficLight,
    ServiceProviderCreate,
    VehicleScheduleRead,
    VehicleScheduleUpsert,
    WorkOrderCreate,
    WorkOrderItemCreate,
    WorkOrderStatusTransition,
)
from manutcar_db.enums import (
    AgreementStatus,
    AuditAction,
    OrgRole,
    VehicleOperationalStatus,
    WorkOrderStatus,
)
from manutcar_db.models.fleet import Vehicle, VehicleManagementAgreement
from manutcar_db.models.maintenance_docs import (
    MaintenancePlan,
    MaintenanceRequest,
    ServiceProvider,
    VehicleMaintenanceSchedule,
    WorkOrder,
    WorkOrderItem,
)

OS_ATTACHMENT_THRESHOLD = Decimal("500.00")
PREVENTIVE_ALERT_KM_MARGIN = 1000
PREVENTIVE_ALERT_DAYS_MARGIN = 15


def _ensure_aware_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _compute_traffic_light(
    schedule: VehicleMaintenanceSchedule,
    current_odometer: int,
    now: datetime,
) -> PreventiveTrafficLight:
    is_overdue = False
    is_due_soon = False

    if schedule.next_due_km is not None:
        if current_odometer >= schedule.next_due_km:
            is_overdue = True
        elif current_odometer >= (schedule.next_due_km - PREVENTIVE_ALERT_KM_MARGIN):
            is_due_soon = True

    if schedule.next_due_date is not None:
        due_dt = _ensure_aware_utc(schedule.next_due_date)
        if now >= due_dt:
            is_overdue = True
        elif now >= (due_dt - timedelta(days=PREVENTIVE_ALERT_DAYS_MARGIN)):
            is_due_soon = True

    if is_overdue:
        return PreventiveTrafficLight.OVERDUE
    if is_due_soon:
        return PreventiveTrafficLight.DUE_SOON
    return PreventiveTrafficLight.OK


async def _ensure_vehicle_access(
    db: AsyncSession,
    org_id: UUID,
    vehicle_id: UUID,
) -> Vehicle:
    vehicle = await db.scalar(
        select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.deleted_at.is_(None),
        )
    )
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veículo não encontrado.",
        )

    agreement = await db.scalar(
        select(VehicleManagementAgreement).where(
            VehicleManagementAgreement.vehicle_id == vehicle_id,
            VehicleManagementAgreement.organization_id == org_id,
            VehicleManagementAgreement.status == AgreementStatus.ACTIVE,
            VehicleManagementAgreement.deleted_at.is_(None),
        )
    )
    if agreement is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organização sem acordo ativo para operar este veículo (RN-FLT-01).",
        )
    return vehicle


async def create_service_provider(
    db: AsyncSession,
    *,
    org_id: UUID,
    actor_user_id: UUID,
    payload: ServiceProviderCreate,
) -> ServiceProvider:
    provider = ServiceProvider(
        organization_id=org_id,
        name=payload.name.strip(),
        document_number=payload.document_number,
        phone=payload.phone,
    )
    db.add(provider)
    await db.flush()

    await record_audit_log(
        db,
        organization_id=org_id,
        actor_user_id=actor_user_id,
        entity_name="ServiceProvider",
        entity_id=provider.id,
        action=AuditAction.CREATE,
        new_values={"name": provider.name, "document_number": provider.document_number},
    )
    await db.commit()
    await db.refresh(provider)
    return provider


async def list_service_providers(
    db: AsyncSession,
    *,
    org_id: UUID,
) -> list[ServiceProvider]:
    result = await db.scalars(
        select(ServiceProvider)
        .where(
            ServiceProvider.organization_id == org_id,
            ServiceProvider.deleted_at.is_(None),
        )
        .order_by(ServiceProvider.name.asc())
    )
    return list(result.all())


async def create_maintenance_plan(
    db: AsyncSession,
    *,
    org_id: UUID,
    actor_user_id: UUID,
    payload: MaintenancePlanCreate,
) -> MaintenancePlan:
    if payload.interval_km is None and payload.interval_days is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe pelo menos interval_km ou interval_days para o plano preventivo.",
        )

    plan = MaintenancePlan(
        organization_id=org_id,
        name=payload.name.strip(),
        interval_km=payload.interval_km,
        interval_days=payload.interval_days,
    )
    db.add(plan)
    await db.flush()

    await record_audit_log(
        db,
        organization_id=org_id,
        actor_user_id=actor_user_id,
        entity_name="MaintenancePlan",
        entity_id=plan.id,
        action=AuditAction.CREATE,
        new_values={
            "name": plan.name,
            "interval_km": plan.interval_km,
            "interval_days": plan.interval_days,
        },
    )
    await db.commit()
    await db.refresh(plan)
    return plan


async def list_maintenance_plans(
    db: AsyncSession,
    *,
    org_id: UUID,
) -> list[MaintenancePlan]:
    result = await db.scalars(
        select(MaintenancePlan)
        .where(
            MaintenancePlan.organization_id == org_id,
            MaintenancePlan.deleted_at.is_(None),
        )
        .order_by(MaintenancePlan.name.asc())
    )
    return list(result.all())

async def upsert_vehicle_schedule(
    db: AsyncSession,
    *,
    org_id: UUID,
    actor_user_id: UUID,
    payload: VehicleScheduleUpsert,
) -> VehicleScheduleRead:
    vehicle = await _ensure_vehicle_access(db, org_id, payload.vehicle_id)

    plan = await db.scalar(
        select(MaintenancePlan).where(
            MaintenancePlan.id == payload.plan_id,
            MaintenancePlan.organization_id == org_id,
            MaintenancePlan.deleted_at.is_(None),
        )
    )
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plano de manutenção não encontrado nesta organização.",
        )

    now = datetime.now(timezone.utc)
    base_km = payload.last_executed_km if payload.last_executed_km is not None else vehicle.current_odometer
    base_date = _ensure_aware_utc(payload.last_executed_at) if payload.last_executed_at else now

    next_due_km = (base_km + plan.interval_km) if plan.interval_km is not None else None
    next_due_date = (base_date + timedelta(days=plan.interval_days)) if plan.interval_days is not None else None

    schedule = await db.scalar(
        select(VehicleMaintenanceSchedule).where(
            VehicleMaintenanceSchedule.vehicle_id == vehicle.id,
            VehicleMaintenanceSchedule.plan_id == plan.id,
        )
    )

    if schedule is None:
        schedule = VehicleMaintenanceSchedule(
            vehicle_id=vehicle.id,
            plan_id=plan.id,
            last_executed_km=base_km,
            last_executed_at=base_date,
            next_due_km=next_due_km,
            next_due_date=next_due_date,
        )
        db.add(schedule)
        action = AuditAction.CREATE
        old_values = None
    else:
        old_values = {
            "last_executed_km": schedule.last_executed_km,
            "next_due_km": schedule.next_due_km,
        }
        schedule.last_executed_km = base_km
        schedule.last_executed_at = base_date
        schedule.next_due_km = next_due_km
        schedule.next_due_date = next_due_date
        action = AuditAction.UPDATE

    await db.flush()
    await record_audit_log(
        db,
        organization_id=org_id,
        actor_user_id=actor_user_id,
        entity_name="VehicleMaintenanceSchedule",
        entity_id=schedule.id,
        action=action,
        old_values=old_values,
        new_values={
            "vehicle_id": str(vehicle.id),
            "plan_id": str(plan.id),
            "next_due_km": next_due_km,
            "next_due_date": next_due_date.isoformat() if next_due_date else None,
        },
    )
    await db.commit()
    await db.refresh(schedule)

    traffic = _compute_traffic_light(schedule, vehicle.current_odometer, now)
    return VehicleScheduleRead(
        id=schedule.id,
        vehicle_id=schedule.vehicle_id,
        plan_id=schedule.plan_id,
        last_executed_km=schedule.last_executed_km,
        last_executed_at=schedule.last_executed_at,
        next_due_km=schedule.next_due_km,
        next_due_date=schedule.next_due_date,
        traffic_light=traffic,
    )


async def list_vehicle_schedules(
    db: AsyncSession,
    *,
    org_id: UUID,
    vehicle_id: UUID,
) -> list[VehicleScheduleRead]:
    vehicle = await _ensure_vehicle_access(db, org_id, vehicle_id)
    now = datetime.now(timezone.utc)

    rows = await db.scalars(
        select(VehicleMaintenanceSchedule)
        .join(MaintenancePlan, MaintenancePlan.id == VehicleMaintenanceSchedule.plan_id)
        .where(
            VehicleMaintenanceSchedule.vehicle_id == vehicle.id,
            MaintenancePlan.organization_id == org_id,
            MaintenancePlan.deleted_at.is_(None),
        )
    )
    items: list[VehicleScheduleRead] = []
    for sched in rows.all():
        items.append(
            VehicleScheduleRead(
                id=sched.id,
                vehicle_id=sched.vehicle_id,
                plan_id=sched.plan_id,
                last_executed_km=sched.last_executed_km,
                last_executed_at=sched.last_executed_at,
                next_due_km=sched.next_due_km,
                next_due_date=sched.next_due_date,
                traffic_light=_compute_traffic_light(sched, vehicle.current_odometer, now),
            )
        )
    return items


async def create_maintenance_request(
    db: AsyncSession,
    *,
    org_id: UUID,
    actor_user_id: UUID,
    payload: MaintenanceRequestCreate,
) -> MaintenanceRequest:
    await _ensure_vehicle_access(db, org_id, payload.vehicle_id)

    req = MaintenanceRequest(
        organization_id=org_id,
        vehicle_id=payload.vehicle_id,
        requested_by_user_id=actor_user_id,
        description=payload.description.strip(),
        status="PENDING",
    )
    db.add(req)
    await db.flush()

    await record_audit_log(
        db,
        organization_id=org_id,
        actor_user_id=actor_user_id,
        entity_name="MaintenanceRequest",
        entity_id=req.id,
        action=AuditAction.CREATE,
        new_values={"vehicle_id": str(req.vehicle_id), "status": req.status},
    )
    await db.commit()
    await db.refresh(req)
    return req


async def list_maintenance_requests(
    db: AsyncSession,
    *,
    org_id: UUID,
    actor_user_id: UUID,
    actor_role: OrgRole,
) -> list[MaintenanceRequest]:
    stmt = select(MaintenanceRequest).where(MaintenanceRequest.organization_id == org_id)
    if actor_role == OrgRole.DRIVER:
        stmt = stmt.where(MaintenanceRequest.requested_by_user_id == actor_user_id)
    stmt = stmt.order_by(MaintenanceRequest.created_at.desc())
    result = await db.scalars(stmt)
    return list(result.all())

async def _get_work_order_for_org(
    db: AsyncSession,
    *,
    org_id: UUID,
    work_order_id: UUID,
) -> WorkOrder:
    wo = await db.scalar(
        select(WorkOrder)
        .options(selectinload(WorkOrder.items))
        .where(
            WorkOrder.id == work_order_id,
            WorkOrder.organization_id == org_id,
            WorkOrder.deleted_at.is_(None),
        )
    )
    if wo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ordem de Serviço não encontrada nesta organização.",
        )
    return wo


async def create_work_order(
    db: AsyncSession,
    *,
    org_id: UUID,
    actor_user_id: UUID,
    payload: WorkOrderCreate,
) -> WorkOrder:
    vehicle = await _ensure_vehicle_access(db, org_id, payload.vehicle_id)

    if payload.odometer_km < vehicle.current_odometer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Odômetro da OS ({payload.odometer_km} km) não pode ser menor que o atual do veículo ({vehicle.current_odometer} km).",
        )

    if payload.service_provider_id is not None:
        provider = await db.scalar(
            select(ServiceProvider).where(
                ServiceProvider.id == payload.service_provider_id,
                ServiceProvider.organization_id == org_id,
                ServiceProvider.deleted_at.is_(None),
            )
        )
        if provider is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fornecedor/oficina não encontrado nesta organização.",
            )

    if payload.request_id is not None:
        req = await db.scalar(
            select(MaintenanceRequest).where(
                MaintenanceRequest.id == payload.request_id,
                MaintenanceRequest.organization_id == org_id,
            )
        )
        if req is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solicitação de manutenção não encontrada nesta organização.",
            )
        req.status = "IN_PROGRESS"

    now = datetime.now(timezone.utc)
    wo = WorkOrder(
        organization_id=org_id,
        vehicle_id=vehicle.id,
        service_provider_id=payload.service_provider_id,
        maintenance_type=payload.maintenance_type,
        status=WorkOrderStatus.OPEN,
        odometer_km=payload.odometer_km,
        total_amount=Decimal("0.00"),
        opened_at=now,
    )
    db.add(wo)

    if payload.odometer_km > vehicle.current_odometer:
        vehicle.current_odometer = payload.odometer_km

    if payload.set_vehicle_in_maintenance:
        vehicle.operational_status = VehicleOperationalStatus.MAINTENANCE

    await db.flush()

    await record_audit_log(
        db,
        organization_id=org_id,
        actor_user_id=actor_user_id,
        entity_name="WorkOrder",
        entity_id=wo.id,
        action=AuditAction.CREATE,
        new_values={
            "vehicle_id": str(wo.vehicle_id),
            "maintenance_type": wo.maintenance_type.value,
            "status": wo.status.value,
            "odometer_km": wo.odometer_km,
        },
    )
    await db.commit()
    return await _get_work_order_for_org(db, org_id=org_id, work_order_id=wo.id)


async def add_work_order_item(
    db: AsyncSession,
    *,
    org_id: UUID,
    actor_user_id: UUID,
    work_order_id: UUID,
    payload: WorkOrderItemCreate,
) -> WorkOrder:
    wo = await _get_work_order_for_org(db, org_id=org_id, work_order_id=work_order_id)

    if wo.status in {WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível adicionar itens a uma OS concluída ou cancelada.",
        )

    if not payload.force_warranty_override:
        past_items = await db.scalars(
            select(WorkOrderItem)
            .join(WorkOrder, WorkOrder.id == WorkOrderItem.work_order_id)
            .where(
                WorkOrder.organization_id == org_id,
                WorkOrder.vehicle_id == wo.vehicle_id,
                WorkOrder.id != wo.id,
                WorkOrder.status == WorkOrderStatus.COMPLETED,
                WorkOrder.deleted_at.is_(None),
                WorkOrderItem.description.ilike(payload.description.strip()),
            )
        )
        now = datetime.now(timezone.utc)
        for prev in past_items.all():
            prev_wo = await db.get(WorkOrder, prev.work_order_id)
            if prev_wo is None:
                continue
            in_time = (
                prev.warranty_days is not None
                and prev_wo.completed_at is not None
                and now <= (_ensure_aware_utc(prev_wo.completed_at) + timedelta(days=prev.warranty_days))
            )
            in_km = (
                prev.warranty_km is not None
                and wo.odometer_km <= (prev_wo.odometer_km + prev.warranty_km)
            )
            if in_time or in_km:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "WARRANTY_COVERAGE_DETECTED",
                        "message": "Item possui cobertura de garantia vigente de OS anterior (RN-MNT-07).",
                        "previous_work_order_id": str(prev_wo.id),
                    },
                )

    total_price = (payload.quantity * payload.unit_price).quantize(Decimal("0.01"))
    item = WorkOrderItem(
        work_order_id=wo.id,
        item_type=getattr(payload, "item_type", "PART") or "PART",
        description=payload.description.strip(),
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        warranty_days=payload.warranty_days,
        warranty_km=payload.warranty_km,
    )
    db.add(item)
    await db.flush()

    wo.total_amount = (wo.total_amount + total_price).quantize(Decimal("0.01"))

    await record_audit_log(
        db,
        organization_id=org_id,
        actor_user_id=actor_user_id,
        entity_name="WorkOrderItem",
        entity_id=item.id,
        action=AuditAction.CREATE,
        new_values={
            "work_order_id": str(wo.id),
            "description": item.description,
            "total_price": str(total_price),
            "work_order_total_amount": str(wo.total_amount),
        },
    )
    await db.commit()
    return await _get_work_order_for_org(db, org_id=org_id, work_order_id=wo.id)

async def transition_work_order_status(
    db: AsyncSession,
    *,
    org_id: UUID,
    actor_user_id: UUID,
    work_order_id: UUID,
    payload: WorkOrderStatusTransition,
) -> WorkOrder:
    wo = await _get_work_order_for_org(db, org_id=org_id, work_order_id=work_order_id)

    if wo.status in {WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OS já está finalizada com status {wo.status.value}.",
        )

    if payload.odometer_km is not None:
        if payload.odometer_km < wo.odometer_km:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Odômetro de fechamento não pode ser menor que o de abertura da OS.",
            )
        wo.odometer_km = payload.odometer_km

    if payload.status == WorkOrderStatus.COMPLETED:
        if wo.total_amount > OS_ATTACHMENT_THRESHOLD and not payload.has_attachments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "MISSING_ATTACHMENT",
                    "message": f"OS acima de R$ {OS_ATTACHMENT_THRESHOLD} exige comprovante/nota fiscal anexada (RN-MNT-08).",
                },
            )

    before_status = wo.status.value
    wo.status = payload.status
    if payload.notes:
        wo.notes = payload.notes

    vehicle = await db.get(Vehicle, wo.vehicle_id)
    if vehicle is not None:
        if wo.odometer_km > vehicle.current_odometer:
            vehicle.current_odometer = wo.odometer_km
        if payload.status == WorkOrderStatus.IN_PROGRESS:
            vehicle.operational_status = VehicleOperationalStatus.MAINTENANCE
        elif payload.status in {WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED}:
            if vehicle.operational_status == VehicleOperationalStatus.MAINTENANCE:
                vehicle.operational_status = VehicleOperationalStatus.ACTIVE

    if payload.status == WorkOrderStatus.COMPLETED:
        wo.completed_at = datetime.now(timezone.utc)

    await record_audit_log(
        db,
        organization_id=org_id,
        actor_user_id=actor_user_id,
        entity_name="WorkOrder",
        entity_id=wo.id,
        action=AuditAction.APPROVE if payload.status == WorkOrderStatus.COMPLETED else AuditAction.UPDATE,
        old_values={"status": before_status},
        new_values={
            "status": wo.status.value,
            "total_amount": str(wo.total_amount),
            "odometer_km": wo.odometer_km,
        },
    )
    await db.commit()
    return await _get_work_order_for_org(db, org_id=org_id, work_order_id=wo.id)


async def list_work_orders(
    db: AsyncSession,
    *,
    org_id: UUID,
    vehicle_id: Optional[UUID] = None,
    status_filter: Optional[WorkOrderStatus] = None,
) -> list[WorkOrder]:
    stmt = (
        select(WorkOrder)
        .options(selectinload(WorkOrder.items))
        .where(WorkOrder.organization_id == org_id, WorkOrder.deleted_at.is_(None))
    )
    if vehicle_id is not None:
        stmt = stmt.where(WorkOrder.vehicle_id == vehicle_id)
    if status_filter is not None:
        stmt = stmt.where(WorkOrder.status == status_filter)
    result = await db.scalars(stmt.order_by(WorkOrder.opened_at.desc()))
    return list(result.all())
