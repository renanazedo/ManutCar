import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import AuthContext, get_current_auth_context, require_roles
from apps.api.app.db.session import get_db
from apps.api.app.services.fleet_service import FleetService
from manutcar.schemas.fleet import (
    VehicleCreate,
    VehicleManagementAgreementCreate,
    VehicleManagementAgreementResponse,
    VehicleManagementAgreementStatusUpdate,
    VehicleOdometerUpdate,
    VehicleOwnerCreate,
    VehicleOwnerResponse,
    VehicleOwnerUpdate,
    VehicleOwnershipHistoryResponse,
    VehicleResponse,
    VehicleTransferOwnership,
    VehicleUpdate,
)
from manutcar_db.enums import OrgRole

router = APIRouter(prefix="/fleet", tags=["Fleet (MC-FLT)"])

_WRITE_ROLES = (OrgRole.OWNER, OrgRole.ADMIN, OrgRole.FLEET_MANAGER)


@router.post("/owners", response_model=VehicleOwnerResponse, status_code=status.HTTP_201_CREATED)
async def create_owner(
    payload: VehicleOwnerCreate,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_WRITE_ROLES)),
):
    owner = await FleetService.create_owner(db, actor, payload)
    await db.commit()
    await db.refresh(owner)
    return owner


@router.get("/owners", response_model=list[VehicleOwnerResponse])
async def list_owners(
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(get_current_auth_context),
):
    return await FleetService.list_owners(db, actor)


@router.get("/owners/{owner_id}", response_model=VehicleOwnerResponse)
async def get_owner(
    owner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(get_current_auth_context),
):
    return await FleetService.get_owner(db, actor, owner_id)


@router.patch("/owners/{owner_id}", response_model=VehicleOwnerResponse)
async def update_owner(
    owner_id: uuid.UUID,
    payload: VehicleOwnerUpdate,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_WRITE_ROLES)),
):
    owner = await FleetService.update_owner(db, actor, owner_id, payload)
    await db.commit()
    await db.refresh(owner)
    return owner


@router.post("/vehicles", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    payload: VehicleCreate,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_WRITE_ROLES)),
):
    vehicle = await FleetService.create_vehicle(db, actor, payload)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.get("/vehicles", response_model=list[VehicleResponse])
async def list_vehicles(
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(get_current_auth_context),
):
    return await FleetService.list_vehicles(db, actor)


@router.get("/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(
    vehicle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(get_current_auth_context),
):
    return await FleetService.get_vehicle(db, actor, vehicle_id)


@router.patch("/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: uuid.UUID,
    payload: VehicleUpdate,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_WRITE_ROLES)),
):
    vehicle = await FleetService.update_vehicle(db, actor, vehicle_id, payload)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.patch("/vehicles/{vehicle_id}/odometer", response_model=VehicleResponse)
async def update_vehicle_odometer(
    vehicle_id: uuid.UUID,
    payload: VehicleOdometerUpdate,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_WRITE_ROLES)),
):
    vehicle = await FleetService.update_odometer(db, actor, vehicle_id, payload)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.post("/vehicles/{vehicle_id}/transfer-ownership", response_model=VehicleResponse)
async def transfer_vehicle_ownership(
    vehicle_id: uuid.UUID,
    payload: VehicleTransferOwnership,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_WRITE_ROLES)),
):
    vehicle = await FleetService.transfer_ownership(db, actor, vehicle_id, payload)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.get("/vehicles/{vehicle_id}/ownership-history", response_model=list[VehicleOwnershipHistoryResponse])
async def list_ownership_history(
    vehicle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(get_current_auth_context),
):
    return await FleetService.list_ownership_history(db, actor, vehicle_id)


@router.post("/agreements", response_model=VehicleManagementAgreementResponse, status_code=status.HTTP_201_CREATED)
async def create_agreement(
    payload: VehicleManagementAgreementCreate,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_WRITE_ROLES)),
):
    agreement = await FleetService.create_agreement(db, actor, payload)
    await db.commit()
    await db.refresh(agreement)
    return agreement


@router.get("/agreements", response_model=list[VehicleManagementAgreementResponse])
async def list_agreements(
    vehicle_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(get_current_auth_context),
):
    return await FleetService.list_agreements(db, actor, vehicle_id)


@router.patch("/agreements/{agreement_id}/status", response_model=VehicleManagementAgreementResponse)
async def update_agreement_status(
    agreement_id: uuid.UUID,
    payload: VehicleManagementAgreementStatusUpdate,
    db: AsyncSession = Depends(get_db),
    actor: AuthContext = Depends(require_roles(*_WRITE_ROLES)),
):
    agreement = await FleetService.update_agreement_status(db, actor, agreement_id, payload)
    await db.commit()
    await db.refresh(agreement)
    return agreement
