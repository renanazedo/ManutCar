from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import AuthContext, require_roles
from apps.api.app.db.session import get_db
from apps.api.app.services import maintenance_service
from manutcar.schemas.maintenance import (
    MaintenancePlanCreate,
    MaintenancePlanRead,
    MaintenanceRequestCreate,
    MaintenanceRequestRead,
    ServiceProviderCreate,
    ServiceProviderRead,
    VehicleScheduleRead,
    VehicleScheduleUpsert,
    WorkOrderCreate,
    WorkOrderItemCreate,
    WorkOrderRead,
    WorkOrderStatus,
    WorkOrderStatusTransition,
)
from manutcar_db.enums import OrgRole

router = APIRouter(prefix="/maintenance", tags=["Maintenance (MC-MNT)"])

ALL_ORG_ROLES = (
    OrgRole.OWNER,
    OrgRole.ADMIN,
    OrgRole.FLEET_MANAGER,
    OrgRole.FINANCIAL,
    OrgRole.DRIVER,
    OrgRole.MAINTENANCE,
)

MANAGEMENT_ROLES = (
    OrgRole.OWNER,
    OrgRole.ADMIN,
    OrgRole.FLEET_MANAGER,
    OrgRole.MAINTENANCE,
)

APPROVAL_ROLES = (
    OrgRole.OWNER,
    OrgRole.ADMIN,
    OrgRole.FLEET_MANAGER,
)


@router.post("/providers", response_model=ServiceProviderRead, status_code=status.HTTP_201_CREATED)
async def create_provider(
    payload: ServiceProviderCreate,
    ctx: AuthContext = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> ServiceProviderRead:
    provider = await maintenance_service.create_service_provider(
        db, org_id=ctx.organization.id, actor_user_id=ctx.user.id, payload=payload
    )
    return ServiceProviderRead.model_validate(provider)


@router.get("/providers", response_model=list[ServiceProviderRead])
async def list_providers(
    ctx: AuthContext = Depends(require_roles(*ALL_ORG_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> list[ServiceProviderRead]:
    providers = await maintenance_service.list_service_providers(db, org_id=ctx.organization.id)
    return [ServiceProviderRead.model_validate(p) for p in providers]


@router.post("/plans", response_model=MaintenancePlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan(
    payload: MaintenancePlanCreate,
    ctx: AuthContext = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> MaintenancePlanRead:
    plan = await maintenance_service.create_maintenance_plan(
        db, org_id=ctx.organization.id, actor_user_id=ctx.user.id, payload=payload
    )
    return MaintenancePlanRead.model_validate(plan)


@router.get("/plans", response_model=list[MaintenancePlanRead])
async def list_plans(
    ctx: AuthContext = Depends(require_roles(*ALL_ORG_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> list[MaintenancePlanRead]:
    plans = await maintenance_service.list_maintenance_plans(db, org_id=ctx.organization.id)
    return [MaintenancePlanRead.model_validate(p) for p in plans]


@router.post("/schedules", response_model=VehicleScheduleRead, status_code=status.HTTP_201_CREATED)
async def upsert_schedule(
    payload: VehicleScheduleUpsert,
    ctx: AuthContext = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> VehicleScheduleRead:
    return await maintenance_service.upsert_vehicle_schedule(
        db, org_id=ctx.organization.id, actor_user_id=ctx.user.id, payload=payload
    )


@router.get("/vehicles/{vehicle_id}/schedules", response_model=list[VehicleScheduleRead])
async def get_vehicle_schedules(
    vehicle_id: UUID,
    ctx: AuthContext = Depends(require_roles(*ALL_ORG_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> list[VehicleScheduleRead]:
    return await maintenance_service.list_vehicle_schedules(
        db, org_id=ctx.organization.id, vehicle_id=vehicle_id
    )

@router.post("/requests", response_model=MaintenanceRequestRead, status_code=status.HTTP_201_CREATED)
async def create_request(
    payload: MaintenanceRequestCreate,
    ctx: AuthContext = Depends(require_roles(*ALL_ORG_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceRequestRead:
    req = await maintenance_service.create_maintenance_request(
        db, org_id=ctx.organization.id, actor_user_id=ctx.user.id, payload=payload
    )
    return MaintenanceRequestRead.model_validate(req)


@router.get("/requests", response_model=list[MaintenanceRequestRead])
async def list_requests(
    ctx: AuthContext = Depends(require_roles(*ALL_ORG_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> list[MaintenanceRequestRead]:
    reqs = await maintenance_service.list_maintenance_requests(
        db,
        org_id=ctx.organization.id,
        actor_user_id=ctx.user.id,
        actor_role=ctx.membership.role,
    )
    return [MaintenanceRequestRead.model_validate(r) for r in reqs]


@router.post("/work-orders", response_model=WorkOrderRead, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    payload: WorkOrderCreate,
    ctx: AuthContext = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> WorkOrderRead:
    wo = await maintenance_service.create_work_order(
        db, org_id=ctx.organization.id, actor_user_id=ctx.user.id, payload=payload
    )
    return WorkOrderRead.model_validate(wo)


@router.get("/work-orders", response_model=list[WorkOrderRead])
async def list_work_orders(
    vehicle_id: Optional[UUID] = Query(default=None),
    status_filter: Optional[WorkOrderStatus] = Query(default=None, alias="status"),
    ctx: AuthContext = Depends(require_roles(*ALL_ORG_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> list[WorkOrderRead]:
    orders = await maintenance_service.list_work_orders(
        db, org_id=ctx.organization.id, vehicle_id=vehicle_id, status_filter=status_filter
    )
    return [WorkOrderRead.model_validate(o) for o in orders]


@router.post("/work-orders/{work_order_id}/items", response_model=WorkOrderRead, status_code=status.HTTP_201_CREATED)
async def add_work_order_item(
    work_order_id: UUID,
    payload: WorkOrderItemCreate,
    ctx: AuthContext = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> WorkOrderRead:
    wo = await maintenance_service.add_work_order_item(
        db,
        org_id=ctx.organization.id,
        actor_user_id=ctx.user.id,
        work_order_id=work_order_id,
        payload=payload,
    )
    return WorkOrderRead.model_validate(wo)


@router.patch("/work-orders/{work_order_id}/status", response_model=WorkOrderRead)
async def update_work_order_status(
    work_order_id: UUID,
    payload: WorkOrderStatusTransition,
    ctx: AuthContext = Depends(require_roles(*APPROVAL_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> WorkOrderRead:
    wo = await maintenance_service.transition_work_order_status(
        db,
        org_id=ctx.organization.id,
        actor_user_id=ctx.user.id,
        work_order_id=work_order_id,
        payload=payload,
    )
    return WorkOrderRead.model_validate(wo)
