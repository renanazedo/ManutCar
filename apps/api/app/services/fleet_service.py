import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import AuthContext
from apps.api.app.services.audit import record_audit_log
from manutcar.schemas.fleet import (
    VehicleCreate,
    VehicleManagementAgreementCreate,
    VehicleManagementAgreementStatusUpdate,
    VehicleOdometerUpdate,
    VehicleOwnerCreate,
    VehicleOwnerUpdate,
    VehicleTransferOwnership,
    VehicleUpdate,
)
from manutcar_db.enums import AgreementStatus, AuditAction
from manutcar_db.models.fleet import (
    Vehicle,
    VehicleManagementAgreement,
    VehicleOwner,
    VehicleOwnershipHistory,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_org_id(actor: AuthContext) -> uuid.UUID:
    if actor.organization.id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Opera??o requer contexto de organiza??o ativo.",
        )
    return actor.organization.id


class FleetService:
    @staticmethod
    async def create_owner(
        db: AsyncSession,
        actor: AuthContext,
        payload: VehicleOwnerCreate,
    ) -> VehicleOwner:
        org_id = _require_org_id(actor)
        existing = await db.scalar(
            select(VehicleOwner).where(
                VehicleOwner.document_number == payload.document_number,
                VehicleOwner.deleted_at.is_(None),
                or_(
                    VehicleOwner.organization_id == org_id,
                    VehicleOwner.organization_id.is_(None),
                ),
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Propriet?rio com este documento j? cadastrado nesta organiza??o.",
            )
        owner = VehicleOwner(
            organization_id=org_id,
            user_id=payload.user_id,
            owner_type=payload.owner_type,
            legal_name=payload.legal_name,
            document_number=payload.document_number,
        )
        db.add(owner)
        await db.flush()
        await record_audit_log(
            db=db,
            organization_id=org_id,
            actor_user_id=actor.user.id,
            action=AuditAction.CREATE,
            entity_type="VehicleOwner",
            entity_id=owner.id,
            new_data={
                "owner_type": owner.owner_type,
                "legal_name": owner.legal_name,
                "document_number": owner.document_number,
            },
        )
        return owner

    @staticmethod
    async def list_owners(db: AsyncSession, actor: AuthContext) -> list[VehicleOwner]:
        org_id = _require_org_id(actor)
        stmt = (
            select(VehicleOwner)
            .where(VehicleOwner.organization_id == org_id, VehicleOwner.deleted_at.is_(None))
            .order_by(VehicleOwner.legal_name.asc())
        )
        return list((await db.scalars(stmt)).all())

    @staticmethod
    async def get_owner(db: AsyncSession, actor: AuthContext, owner_id: uuid.UUID) -> VehicleOwner:
        org_id = _require_org_id(actor)
        owner = await db.scalar(
            select(VehicleOwner).where(
                VehicleOwner.id == owner_id,
                VehicleOwner.organization_id == org_id,
                VehicleOwner.deleted_at.is_(None),
            )
        )
        if owner is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Propriet?rio n?o encontrado.")
        return owner

    @staticmethod
    async def update_owner(
        db: AsyncSession, actor: AuthContext, owner_id: uuid.UUID, payload: VehicleOwnerUpdate
    ) -> VehicleOwner:
        org_id = _require_org_id(actor)
        owner = await FleetService.get_owner(db, actor, owner_id)
        old_data = {"legal_name": owner.legal_name, "user_id": str(owner.user_id) if owner.user_id else None}
        if payload.legal_name is not None:
            owner.legal_name = payload.legal_name
        if payload.user_id is not None:
            owner.user_id = payload.user_id
        await db.flush()
        await record_audit_log(
            db=db, organization_id=org_id, actor_user_id=actor.user.id,
            action=AuditAction.UPDATE, entity_type="VehicleOwner", entity_id=owner.id,
            old_data=old_data,
            new_data={"legal_name": owner.legal_name, "user_id": str(owner.user_id) if owner.user_id else None},
        )
        return owner

    @staticmethod
    async def create_vehicle(db: AsyncSession, actor: AuthContext, payload: VehicleCreate) -> Vehicle:
        org_id = _require_org_id(actor)
        owner = await FleetService.get_owner(db, actor, payload.current_owner_id)
        dup = await db.scalar(select(Vehicle).where(Vehicle.plate == payload.plate, Vehicle.deleted_at.is_(None)))
        if dup is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Placa j? cadastrada.")
        now = payload.agreement_start_date or _utcnow()
        vehicle = Vehicle(
            plate=payload.plate, renavam=payload.renavam, chassis=payload.chassis,
            brand=payload.brand, model=payload.model,
            year_manufacture=payload.year_manufacture, year_model=payload.year_model,
            fuel_type=payload.fuel_type, current_odometer=payload.current_odometer,
            operational_status=payload.operational_status, current_owner_id=owner.id,
        )
        db.add(vehicle)
        await db.flush()
        history = VehicleOwnershipHistory(vehicle_id=vehicle.id, owner_id=owner.id, start_date=now, end_date=None)
        agreement = VehicleManagementAgreement(
            vehicle_id=vehicle.id, organization_id=org_id, owner_id=owner.id,
            status=AgreementStatus.ACTIVE, start_date=now, end_date=None,
        )
        db.add_all([history, agreement])
        await db.flush()
        await record_audit_log(
            db=db, organization_id=org_id, actor_user_id=actor.user.id,
            action=AuditAction.CREATE, entity_type="Vehicle", entity_id=vehicle.id,
            new_data={"plate": vehicle.plate, "current_odometer": vehicle.current_odometer, "owner_id": str(owner.id)},
        )
        return vehicle

    @staticmethod
    async def list_vehicles(db: AsyncSession, actor: AuthContext) -> list[Vehicle]:
        org_id = _require_org_id(actor)
        stmt = (
            select(Vehicle)
            .join(
                VehicleManagementAgreement,
                and_(
                    VehicleManagementAgreement.vehicle_id == Vehicle.id,
                    VehicleManagementAgreement.organization_id == org_id,
                    VehicleManagementAgreement.status == AgreementStatus.ACTIVE,
                    VehicleManagementAgreement.deleted_at.is_(None),
                ),
            )
            .where(Vehicle.deleted_at.is_(None))
            .order_by(Vehicle.plate.asc())
        )
        return list((await db.scalars(stmt)).unique().all())

    @staticmethod
    async def get_vehicle(db: AsyncSession, actor: AuthContext, vehicle_id: uuid.UUID) -> Vehicle:
        org_id = _require_org_id(actor)
        stmt = (
            select(Vehicle)
            .join(
                VehicleManagementAgreement,
                and_(
                    VehicleManagementAgreement.vehicle_id == Vehicle.id,
                    VehicleManagementAgreement.organization_id == org_id,
                    VehicleManagementAgreement.status == AgreementStatus.ACTIVE,
                    VehicleManagementAgreement.deleted_at.is_(None),
                ),
            )
            .where(Vehicle.id == vehicle_id, Vehicle.deleted_at.is_(None))
        )
        vehicle = await db.scalar(stmt)
        if vehicle is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ve?culo n?o encontrado.")
        return vehicle

    @staticmethod
    async def update_vehicle(
        db: AsyncSession, actor: AuthContext, vehicle_id: uuid.UUID, payload: VehicleUpdate
    ) -> Vehicle:
        org_id = _require_org_id(actor)
        vehicle = await FleetService.get_vehicle(db, actor, vehicle_id)
        old_data = {"brand": vehicle.brand, "model": vehicle.model, "status": vehicle.operational_status.value}
        for field in ("brand", "model", "fuel_type", "operational_status", "renavam", "chassis"):
            val = getattr(payload, field)
            if val is not None:
                setattr(vehicle, field, val)
        await db.flush()
        await record_audit_log(
            db=db, organization_id=org_id, actor_user_id=actor.user.id,
            action=AuditAction.UPDATE, entity_type="Vehicle", entity_id=vehicle.id,
            old_data=old_data,
            new_data={"brand": vehicle.brand, "model": vehicle.model, "status": vehicle.operational_status.value},
            reason=payload.reason,
        )
        return vehicle

    @staticmethod
    async def update_odometer(
        db: AsyncSession, actor: AuthContext, vehicle_id: uuid.UUID, payload: VehicleOdometerUpdate
    ) -> Vehicle:
        org_id = _require_org_id(actor)
        vehicle = await FleetService.get_vehicle(db, actor, vehicle_id)
        if payload.new_odometer.__lt__(vehicle.current_odometer):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Od?metro monot?nico violado: {payload.new_odometer} inferior a {vehicle.current_odometer}.",
            )
        old_odo = vehicle.current_odometer
        vehicle.current_odometer = payload.new_odometer
        await db.flush()
        await record_audit_log(
            db=db, organization_id=org_id, actor_user_id=actor.user.id,
            action=AuditAction.UPDATE, entity_type="Vehicle", entity_id=vehicle.id,
            old_data={"current_odometer": old_odo}, new_data={"current_odometer": vehicle.current_odometer},
            reason=payload.reason or "Atualiza??o de od?metro",
        )
        return vehicle

    @staticmethod
    async def transfer_ownership(
        db: AsyncSession, actor: AuthContext, vehicle_id: uuid.UUID, payload: VehicleTransferOwnership
    ) -> Vehicle:
        org_id = _require_org_id(actor)
        vehicle = await FleetService.get_vehicle(db, actor, vehicle_id)
        new_owner = await FleetService.get_owner(db, actor, payload.new_owner_id)
        if vehicle.current_owner_id == new_owner.id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Mesmo propriet?rio.")
        dt = payload.transfer_date or _utcnow()
        prev_id = vehicle.current_owner_id
        open_hist = await db.scalar(
            select(VehicleOwnershipHistory).where(
                VehicleOwnershipHistory.vehicle_id == vehicle.id,
                VehicleOwnershipHistory.end_date.is_(None),
            )
        )
        if open_hist is not None:
            open_hist.end_date = dt
        db.add(VehicleOwnershipHistory(vehicle_id=vehicle.id, owner_id=new_owner.id, start_date=dt, end_date=None))
        vehicle.current_owner_id = new_owner.id
        await db.flush()
        await record_audit_log(
            db=db, organization_id=org_id, actor_user_id=actor.user.id,
            action=AuditAction.UPDATE, entity_type="Vehicle", entity_id=vehicle.id,
            old_data={"current_owner_id": str(prev_id) if prev_id else None},
            new_data={"current_owner_id": str(new_owner.id)},
            reason=payload.reason or "Transfer?ncia de propriedade",
        )
        return vehicle

    @staticmethod
    async def list_ownership_history(db: AsyncSession, actor: AuthContext, vehicle_id: uuid.UUID) -> list[VehicleOwnershipHistory]:
        await FleetService.get_vehicle(db, actor, vehicle_id)
        stmt = select(VehicleOwnershipHistory).where(VehicleOwnershipHistory.vehicle_id == vehicle_id).order_by(VehicleOwnershipHistory.start_date.desc())
        return list((await db.scalars(stmt)).all())

    @staticmethod
    async def create_agreement(db: AsyncSession, actor: AuthContext, payload: VehicleManagementAgreementCreate) -> VehicleManagementAgreement:
        org_id = _require_org_id(actor)
        owner = await FleetService.get_owner(db, actor, payload.owner_id)
        vehicle = await db.scalar(select(Vehicle).where(Vehicle.id == payload.vehicle_id, Vehicle.deleted_at.is_(None)))
        if vehicle is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ve?culo n?o encontrado.")
        if payload.status == AgreementStatus.ACTIVE:
            active = await db.scalar(
                select(VehicleManagementAgreement).where(
                    VehicleManagementAgreement.vehicle_id == vehicle.id,
                    VehicleManagementAgreement.status == AgreementStatus.ACTIVE,
                    VehicleManagementAgreement.deleted_at.is_(None),
                )
            )
            if active is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ve?culo j? possui acordo ativo.")
        agr = VehicleManagementAgreement(
            vehicle_id=vehicle.id, organization_id=org_id, owner_id=owner.id,
            status=payload.status, start_date=payload.start_date, end_date=payload.end_date,
        )
        db.add(agr)
        await db.flush()
        await record_audit_log(
            db=db, organization_id=org_id, actor_user_id=actor.user.id,
            action=AuditAction.CREATE, entity_type="VehicleManagementAgreement", entity_id=agr.id,
            new_data={"vehicle_id": str(vehicle.id), "owner_id": str(owner.id), "status": agr.status.value},
        )
        return agr

    @staticmethod
    async def list_agreements(db: AsyncSession, actor: AuthContext, vehicle_id: Optional[uuid.UUID] = None) -> list[VehicleManagementAgreement]:
        org_id = _require_org_id(actor)
        conds = [VehicleManagementAgreement.organization_id == org_id, VehicleManagementAgreement.deleted_at.is_(None)]
        if vehicle_id is not None:
            conds.append(VehicleManagementAgreement.vehicle_id == vehicle_id)
        stmt = select(VehicleManagementAgreement).where(*conds).order_by(VehicleManagementAgreement.start_date.desc())
        return list((await db.scalars(stmt)).all())

    @staticmethod
    async def update_agreement_status(
        db: AsyncSession, actor: AuthContext, agreement_id: uuid.UUID, payload: VehicleManagementAgreementStatusUpdate
    ) -> VehicleManagementAgreement:
        org_id = _require_org_id(actor)
        agr = await db.scalar(
            select(VehicleManagementAgreement).where(
                VehicleManagementAgreement.id == agreement_id,
                VehicleManagementAgreement.organization_id == org_id,
                VehicleManagementAgreement.deleted_at.is_(None),
            )
        )
        if agr is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acordo n?o encontrado.")
        old_st = agr.status.value
        agr.status = payload.status
        if payload.end_date is not None:
            agr.end_date = payload.end_date
        elif payload.status in (AgreementStatus.REVOKED, AgreementStatus.EXPIRED) and agr.end_date is None:
            agr.end_date = _utcnow()
        await db.flush()
        await record_audit_log(
            db=db, organization_id=org_id, actor_user_id=actor.user.id,
            action=AuditAction.UPDATE, entity_type="VehicleManagementAgreement", entity_id=agr.id,
            old_data={"status": old_st}, new_data={"status": agr.status.value}, reason=payload.reason,
        )
        return agr
