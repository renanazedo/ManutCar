import uuid
from datetime import datetime, timezone
from typing import Optional

from apps.api.app.core.security import AuthContext
from apps.api.app.services.audit import record_audit_log
from fastapi import HTTPException, status
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
from manutcar_db.enums import AgreementStatus, AuditAction, OrgRole
from manutcar_db.models.fleet import (
    Vehicle,
    VehicleManagementAgreement,
    VehicleOwner,
    VehicleOwnershipHistory,
)
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


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
            entity_name="VehicleOwner",
            entity_id=owner.id,
            new_values={
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
            action=AuditAction.UPDATE, entity_name="VehicleOwner", entity_id=owner.id,
            old_values=old_data,
            new_values={"legal_name": owner.legal_name, "user_id": str(owner.user_id) if owner.user_id else None},
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
            action=AuditAction.CREATE, entity_name="Vehicle", entity_id=vehicle.id,
            new_values={"plate": vehicle.plate, "current_odometer": vehicle.current_odometer, "owner_id": str(owner.id)},
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
            .join(VehicleOwner, Vehicle.current_owner_id == VehicleOwner.id)
            .where(
                VehicleOwner.organization_id == org_id,
                VehicleOwner.deleted_at.is_(None),
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
            .join(VehicleOwner, Vehicle.current_owner_id == VehicleOwner.id)
            .where(
                Vehicle.id == vehicle_id,
                Vehicle.deleted_at.is_(None),
                VehicleOwner.organization_id == org_id,
                VehicleOwner.deleted_at.is_(None),
            )
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
            action=AuditAction.UPDATE, entity_name="Vehicle", entity_id=vehicle.id,
            old_values=old_data,
            new_values={"brand": vehicle.brand, "model": vehicle.model, "status": vehicle.operational_status.value},
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
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Od?metro monot?nico violado: {payload.new_odometer} inferior a {vehicle.current_odometer}.",
            )
        old_odo = vehicle.current_odometer
        vehicle.current_odometer = payload.new_odometer
        await db.flush()
        await record_audit_log(
            db=db, organization_id=org_id, actor_user_id=actor.user.id,
            action=AuditAction.UPDATE, entity_name="Vehicle", entity_id=vehicle.id,
            old_values={"current_odometer": old_odo}, new_values={"current_odometer": vehicle.current_odometer},
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
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Mesmo propriet?rio.")
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
        agreements = list(
            (
                await db.scalars(
                    select(VehicleManagementAgreement).where(
                        VehicleManagementAgreement.vehicle_id == vehicle.id,
                        VehicleManagementAgreement.owner_id != new_owner.id,
                        VehicleManagementAgreement.organization_id != new_owner.organization_id,
                        VehicleManagementAgreement.status.in_(
                            (AgreementStatus.PENDING, AgreementStatus.ACTIVE)
                        ),
                        VehicleManagementAgreement.deleted_at.is_(None),
                    )
                )
            ).all()
        )
        for agreement in agreements:
            old_status = agreement.status.value
            agreement.status = AgreementStatus.REVOKED
            agreement.end_date = dt
            await record_audit_log(
                db=db,
                organization_id=agreement.organization_id,
                actor_user_id=actor.user.id,
                action=AuditAction.REVOKE,
                entity_name="VehicleManagementAgreement",
                entity_id=agreement.id,
                old_values={"status": old_status},
                new_values={"status": agreement.status.value, "end_date": dt.isoformat()},
            )
        await db.flush()
        await record_audit_log(
            db=db, organization_id=org_id, actor_user_id=actor.user.id,
            action=AuditAction.UPDATE, entity_name="Vehicle", entity_id=vehicle.id,
            old_values={"current_owner_id": str(prev_id) if prev_id else None},
            new_values={"current_owner_id": str(new_owner.id)},
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
        vehicle = await db.scalar(select(Vehicle).where(Vehicle.id == payload.vehicle_id, Vehicle.deleted_at.is_(None)))
        if vehicle is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ve?culo n?o encontrado.")
        owner = await db.scalar(
            select(VehicleOwner).where(
                VehicleOwner.id == vehicle.current_owner_id,
                VehicleOwner.deleted_at.is_(None),
            )
        )
        if owner is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ve?culo sem propriet?rio ativo.")
        if owner.id != payload.owner_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="O propriet?rio informado n?o corresponde ao propriet?rio atual do ve?culo.",
            )

        cross_org = owner.organization_id != org_id
        if cross_org and owner.owner_type not in ("PF", "PJ"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Tipo de propriet?rio inv?lido para consentimento entre organiza??es.",
            )
        if cross_org and owner.owner_type == "PF" and owner.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="O propriet?rio PF precisa estar associado a um usu?rio para consentir.",
            )
        if cross_org and owner.owner_type == "PJ" and owner.organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="O propriet?rio PJ precisa estar associado a uma organiza??o para consentir.",
            )

        agreement_status = AgreementStatus.PENDING if cross_org else payload.status
        if agreement_status == AgreementStatus.ACTIVE:
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
            status=agreement_status, start_date=payload.start_date, end_date=payload.end_date,
        )
        db.add(agr)
        await db.flush()
        await record_audit_log(
            db=db, organization_id=org_id, actor_user_id=actor.user.id,
            action=AuditAction.CREATE, entity_name="VehicleManagementAgreement", entity_id=agr.id,
            new_values={"vehicle_id": str(vehicle.id), "owner_id": str(owner.id), "status": agr.status.value},
        )
        return agr

    @staticmethod
    async def list_pending_agreement_consents(
        db: AsyncSession, actor: AuthContext
    ) -> list[VehicleManagementAgreement]:
        owner_conditions = [
            and_(
                VehicleOwner.owner_type == "PF",
                VehicleOwner.user_id == actor.user.id,
            )
        ]
        if actor.membership.role == OrgRole.ADMIN:
            owner_conditions.append(
                and_(
                    VehicleOwner.owner_type == "PJ",
                    VehicleOwner.organization_id == actor.organization.id,
                )
            )

        stmt = (
            select(VehicleManagementAgreement)
            .join(VehicleOwner, VehicleManagementAgreement.owner_id == VehicleOwner.id)
            .join(Vehicle, VehicleManagementAgreement.vehicle_id == Vehicle.id)
            .where(
                VehicleManagementAgreement.status == AgreementStatus.PENDING,
                VehicleManagementAgreement.deleted_at.is_(None),
                VehicleOwner.deleted_at.is_(None),
                Vehicle.deleted_at.is_(None),
                Vehicle.current_owner_id == VehicleOwner.id,
                or_(
                    VehicleOwner.organization_id.is_(None),
                    VehicleManagementAgreement.organization_id != VehicleOwner.organization_id,
                ),
                or_(*owner_conditions),
            )
            .order_by(VehicleManagementAgreement.created_at.desc())
        )
        return list((await db.scalars(stmt)).all())

    @staticmethod
    async def _get_agreement_owner(
        db: AsyncSession, agreement: VehicleManagementAgreement
    ) -> VehicleOwner:
        owner = await db.scalar(
            select(VehicleOwner).where(
                VehicleOwner.id == agreement.owner_id,
                VehicleOwner.deleted_at.is_(None),
            )
        )
        if owner is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Propriet?rio do acordo indispon?vel.")
        return owner

    @staticmethod
    def _require_agreement_owner_authority(actor: AuthContext, owner: VehicleOwner) -> None:
        is_pf_owner = owner.owner_type == "PF" and owner.user_id == actor.user.id
        is_pj_admin = (
            owner.owner_type == "PJ"
            and owner.organization_id == actor.organization.id
            and actor.membership.role == OrgRole.ADMIN
        )
        if not (is_pf_owner or is_pj_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Somente o propriet?rio PF ou um ADMIN da organiza??o propriet?ria pode consentir.",
            )

    @staticmethod
    async def consent_to_agreement(
        db: AsyncSession, actor: AuthContext, agreement_id: uuid.UUID
    ) -> VehicleManagementAgreement:
        agreement = await db.scalar(
            select(VehicleManagementAgreement).where(
                VehicleManagementAgreement.id == agreement_id,
                VehicleManagementAgreement.deleted_at.is_(None),
            )
        )
        if agreement is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acordo n?o encontrado.")
        owner = await FleetService._get_agreement_owner(db, agreement)
        FleetService._require_agreement_owner_authority(actor, owner)
        if agreement.organization_id == owner.organization_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este acordo n?o exige consentimento entre organiza??es.",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A concess?o de acesso entre organiza??es est? indispon?vel "
                "at? a defini??o e implementa??o dos escopos granulares."
            ),
        )

    @staticmethod
    async def revoke_agreement_consent(
        db: AsyncSession, actor: AuthContext, agreement_id: uuid.UUID
    ) -> VehicleManagementAgreement:
        agreement = await db.scalar(
            select(VehicleManagementAgreement).where(
                VehicleManagementAgreement.id == agreement_id,
                VehicleManagementAgreement.deleted_at.is_(None),
            )
        )
        if agreement is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acordo n?o encontrado.")
        owner = await FleetService._get_agreement_owner(db, agreement)
        FleetService._require_agreement_owner_authority(actor, owner)
        if agreement.organization_id == owner.organization_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este acordo n?o exige consentimento entre organiza??es.",
            )
        if agreement.status not in (AgreementStatus.PENDING, AgreementStatus.ACTIVE):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Somente acordos pendentes ou ativos podem ser recusados/revogados.",
            )

        old_status = agreement.status.value
        now = _utcnow()
        agreement.status = AgreementStatus.REVOKED
        agreement.end_date = now
        if agreement.consented_at is not None:
            agreement.consent_revoked_at = now
        await db.flush()
        await record_audit_log(
            db=db,
            organization_id=owner.organization_id,
            actor_user_id=actor.user.id,
            action=AuditAction.REVOKE,
            entity_name="VehicleManagementAgreement",
            entity_id=agreement.id,
            old_values={"status": old_status},
            new_values={
                "status": agreement.status.value,
                "consent_revoked_at": (
                    agreement.consent_revoked_at.isoformat()
                    if agreement.consent_revoked_at is not None
                    else None
                ),
            },
        )
        return agreement

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
        owner = await FleetService._get_agreement_owner(db, agr)
        if owner.organization_id != org_id:
            if payload.status == AgreementStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Acordos entre organiza??es s? podem ser ativados pelo consentimento do propriet?rio.",
                )
            if payload.status == AgreementStatus.PENDING and agr.status != AgreementStatus.PENDING:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Acordos encerrados n?o podem voltar ao estado pendente.",
                )
            if (
                payload.status in (AgreementStatus.REVOKED, AgreementStatus.EXPIRED)
                and agr.status in (AgreementStatus.REVOKED, AgreementStatus.EXPIRED)
                and payload.status != agr.status
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Acordos encerrados n?o podem mudar para outro estado terminal.",
                )
        old_st = agr.status.value
        agr.status = payload.status
        if payload.end_date is not None:
            agr.end_date = payload.end_date
        elif payload.status in (AgreementStatus.REVOKED, AgreementStatus.EXPIRED) and agr.end_date is None:
            agr.end_date = _utcnow()
        await db.flush()
        await record_audit_log(
            db=db, organization_id=org_id, actor_user_id=actor.user.id,
            action=AuditAction.UPDATE, entity_name="VehicleManagementAgreement", entity_id=agr.id,
            old_values={"status": old_st},
            new_values={"status": agr.status.value},
        )
        return agr
