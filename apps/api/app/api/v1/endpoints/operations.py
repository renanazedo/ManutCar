import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import AuthContext, require_roles
from apps.api.app.db.session import get_db
from apps.api.app.services.operations_service import OperationsService
from manutcar.schemas.operations import (
    VehicleAssignmentClose,
    VehicleAssignmentCreate,
    VehicleAssignmentResponse,
    VehicleAssignmentUpdate,
    VehicleFinancialResponsibilityResponse,
    VehicleFinancialResponsibilityUpsert,
)
from manutcar_db.enums import OrgRole

router = APIRouter(prefix="/operations", tags=["Operations (MC-OPS)"])

_ASSIGNMENT_WRITE_ROLES = (OrgRole.OWNER, OrgRole.ADMIN, OrgRole.FLEET_MANAGER)
_ASSIGNMENT_READ_ROLES = (
    OrgRole.OWNER,
    OrgRole.ADMIN,
    OrgRole.FLEET_MANAGER,
    OrgRole.FINANCIAL,
    OrgRole.DRIVER,
)
_FIN_RESP_ROLES = (
    OrgRole.OWNER,
    OrgRole.ADMIN,
    OrgRole.FLEET_MANAGER,
    OrgRole.FINANCIAL,
)


@router.post(
    "/assignments",
    response_model=VehicleAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assignment(
    payload: VehicleAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_ASSIGNMENT_WRITE_ROLES)),
):
    assignment = await OperationsService.create_assignment(db, actor, payload)
    await db.commit()
    await db.refresh(assignment)
    return assignment


@router.get("/assignments", response_model=list[VehicleAssignmentResponse])
async def list_assignments(
    vehicle_id: Optional[uuid.UUID] = Query(default=None),
    driver_user_id: Optional[uuid.UUID] = Query(default=None),
    active_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_ASSIGNMENT_READ_ROLES)),
):
    return await OperationsService.list_assignments(
        db,
        actor,
        vehicle_id=vehicle_id,
        driver_user_id=driver_user_id,
        active_only=active_only,
    )


@router.get("/assignments/{assignment_id}", response_model=VehicleAssignmentResponse)
async def get_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_ASSIGNMENT_READ_ROLES)),
):
    return await OperationsService.get_assignment(db, actor, assignment_id)


@router.patch("/assignments/{assignment_id}", response_model=VehicleAssignmentResponse)
async def update_assignment(
    assignment_id: uuid.UUID,
    payload: VehicleAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_ASSIGNMENT_WRITE_ROLES)),
):
    assignment = await OperationsService.update_assignment(db, actor, assignment_id, payload)
    await db.commit()
    await db.refresh(assignment)
    return assignment


@router.post("/assignments/{assignment_id}/close", response_model=VehicleAssignmentResponse)
async def close_assignment(
    assignment_id: uuid.UUID,
    payload: VehicleAssignmentClose = VehicleAssignmentClose(),
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_ASSIGNMENT_WRITE_ROLES)),
):
    assignment = await OperationsService.close_assignment(db, actor, assignment_id, payload)
    await db.commit()
    await db.refresh(assignment)
    return assignment


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_ASSIGNMENT_WRITE_ROLES)),
):
    await OperationsService.delete_assignment(db, actor, assignment_id)
    await db.commit()


@router.put(
    "/financial-responsibilities",
    response_model=VehicleFinancialResponsibilityResponse,
)
async def upsert_financial_responsibility(
    payload: VehicleFinancialResponsibilityUpsert,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_FIN_RESP_ROLES)),
):
    rule = await OperationsService.upsert_financial_responsibility(db, actor, payload)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get(
    "/financial-responsibilities",
    response_model=list[VehicleFinancialResponsibilityResponse],
)
async def list_financial_responsibilities(
    vehicle_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_FIN_RESP_ROLES)),
):
    return await OperationsService.list_financial_responsibilities(
        db, actor, vehicle_id=vehicle_id
    )


@router.delete(
    "/financial-responsibilities/{responsibility_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_financial_responsibility(
    responsibility_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_FIN_RESP_ROLES)),
):
    await OperationsService.delete_financial_responsibility(db, actor, responsibility_id)
    await db.commit()
