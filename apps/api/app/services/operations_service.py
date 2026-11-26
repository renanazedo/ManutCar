import uuid
from datetime import datetime, timezone
from typing import Optional

from apps.api.app.core.security import AuthContext
from apps.api.app.services.audit import record_audit_log
from fastapi import HTTPException, status
from manutcar.schemas.operations import (
    VehicleAssignmentClose,
    VehicleAssignmentCreate,
    VehicleAssignmentUpdate,
    VehicleFinancialResponsibilityUpsert,
)
from manutcar_db.enums import AgreementStatus, AuditAction, OrgRole
from manutcar_db.models.fleet import (
    Vehicle,
    VehicleAssignment,
    VehicleFinancialResponsibility,
    VehicleManagementAgreement,
    VehicleOwner,
)
from manutcar_db.models.identity import OrganizationMember
from sqlalchemy import and_, not_, select
from sqlalchemy.ext.asyncio import AsyncSession


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _require_org_id(actor: AuthContext) -> uuid.UUID:
    if actor.organization.id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operação requer contexto de organização ativo.",
        )
    return actor.organization.id


async def _assert_vehicle_in_org(
    db: AsyncSession, org_id: uuid.UUID, vehicle_id: uuid.UUID
) -> Vehicle:
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
        .where(Vehicle.id == vehicle_id, Vehicle.deleted_at.is_(None))
        .where(
            VehicleOwner.organization_id == org_id,
            VehicleOwner.deleted_at.is_(None),
        )
    )
    vehicle = await db.scalar(stmt)
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veículo não encontrado ou sem acordo de gestão ativo nesta organização.",
        )
    return vehicle


class OperationsService:
    @staticmethod
    async def create_assignment(
        db: AsyncSession,
        actor: AuthContext,
        payload: VehicleAssignmentCreate,
    ) -> VehicleAssignment:
        org_id = _require_org_id(actor)
        await _assert_vehicle_in_org(db, org_id, payload.vehicle_id)

        driver_member = await db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == payload.driver_user_id,
                OrganizationMember.is_active.is_(True),
            )
        )
        if driver_member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Motorista não encontrado ou inativo nesta organização.",
            )

        existing_stmt = select(VehicleAssignment).where(
            VehicleAssignment.organization_id == org_id,
            VehicleAssignment.driver_user_id == payload.driver_user_id,
            VehicleAssignment.deleted_at.is_(None),
        )
        existing_assignments = list((await db.scalars(existing_stmt)).all())

        new_start = _as_utc(payload.start_datetime)
        new_end = _as_utc(payload.end_datetime) if payload.end_datetime else None

        for existing in existing_assignments:
            ex_start = _as_utc(existing.start_datetime)
            ex_end = _as_utc(existing.end_datetime) if existing.end_datetime else None

            starts_before_ex_ends = ex_end is None or ex_end > new_start
            ex_starts_before_new_ends = new_end is None or new_end > ex_start

            if starts_before_ex_ends and ex_starts_before_new_ends:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Motorista já possui alocação vigente ou sobreposta neste intervalo (RN-FLT-06).",
                )

        assignment = VehicleAssignment(
            vehicle_id=payload.vehicle_id,
            organization_id=org_id,
            driver_user_id=payload.driver_user_id,
            start_datetime=new_start,
            end_datetime=new_end,
            shift_label=payload.shift_label,
        )
        db.add(assignment)
        await db.flush()

        await record_audit_log(
            db=db,
            organization_id=org_id,
            actor_user_id=actor.user.id,
            action=AuditAction.CREATE,
            entity_name="VehicleAssignment",
            entity_id=assignment.id,
            new_values={
                "vehicle_id": str(assignment.vehicle_id),
                "driver_user_id": str(assignment.driver_user_id),
                "start_datetime": assignment.start_datetime.isoformat(),
                "end_datetime": assignment.end_datetime.isoformat() if assignment.end_datetime else None,
                "shift_label": assignment.shift_label,
            },
        )
        return assignment

    @staticmethod
    async def list_assignments(
        db: AsyncSession,
        actor: AuthContext,
        vehicle_id: Optional[uuid.UUID] = None,
        driver_user_id: Optional[uuid.UUID] = None,
        active_only: bool = False,
    ) -> list[VehicleAssignment]:
        org_id = _require_org_id(actor)
        conds = [
            VehicleAssignment.organization_id == org_id,
            VehicleAssignment.deleted_at.is_(None),
        ]

        if actor.membership and actor.membership.role == OrgRole.DRIVER:
            conds.append(VehicleAssignment.driver_user_id == actor.user.id)
        elif driver_user_id is not None:
            conds.append(VehicleAssignment.driver_user_id == driver_user_id)

        if vehicle_id is not None:
            conds.append(VehicleAssignment.vehicle_id == vehicle_id)

        if active_only:
            now = _utcnow()
            conds.append(not_(VehicleAssignment.start_datetime > now))
            conds.append(
                (VehicleAssignment.end_datetime.is_(None))
                | (VehicleAssignment.end_datetime > now)
            )

        stmt = (
            select(VehicleAssignment)
            .where(*conds)
            .order_by(VehicleAssignment.start_datetime.desc())
        )
        return list((await db.scalars(stmt)).all())

    @staticmethod
    async def get_assignment(
        db: AsyncSession,
        actor: AuthContext,
        assignment_id: uuid.UUID,
    ) -> VehicleAssignment:
        org_id = _require_org_id(actor)
        conds = [
            VehicleAssignment.id == assignment_id,
            VehicleAssignment.organization_id == org_id,
            VehicleAssignment.deleted_at.is_(None),
        ]
        if actor.membership and actor.membership.role == OrgRole.DRIVER:
            conds.append(VehicleAssignment.driver_user_id == actor.user.id)

        assignment = await db.scalar(select(VehicleAssignment).where(*conds))
        if assignment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alocação de motorista não encontrada.",
            )
        return assignment
    @staticmethod
    async def update_assignment(
        db: AsyncSession,
        actor: AuthContext,
        assignment_id: uuid.UUID,
        payload: VehicleAssignmentUpdate,
    ) -> VehicleAssignment:
        org_id = _require_org_id(actor)
        assignment = await OperationsService.get_assignment(db, actor, assignment_id)

        old_values = {
            "end_datetime": assignment.end_datetime.isoformat() if assignment.end_datetime else None,
            "shift_label": assignment.shift_label,
        }

        if payload.end_datetime is not None:
            new_end = _as_utc(payload.end_datetime)
            if not (new_end > _as_utc(assignment.start_datetime)):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="end_datetime deve ser posterior a start_datetime.",
                )
            assignment.end_datetime = new_end

        if payload.shift_label is not None:
            assignment.shift_label = payload.shift_label

        await db.flush()
        await record_audit_log(
            db=db,
            organization_id=org_id,
            actor_user_id=actor.user.id,
            action=AuditAction.UPDATE,
            entity_name="VehicleAssignment",
            entity_id=assignment.id,
            old_values=old_values,
            new_values={
                "end_datetime": assignment.end_datetime.isoformat() if assignment.end_datetime else None,
                "shift_label": assignment.shift_label,
            },
        )
        return assignment

    @staticmethod
    async def close_assignment(
        db: AsyncSession,
        actor: AuthContext,
        assignment_id: uuid.UUID,
        payload: VehicleAssignmentClose,
    ) -> VehicleAssignment:
        org_id = _require_org_id(actor)
        assignment = await OperationsService.get_assignment(db, actor, assignment_id)

        if assignment.end_datetime is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Esta alocação já foi encerrada.",
            )

        end_dt = _as_utc(payload.end_datetime) if payload.end_datetime else _utcnow()
        if not (end_dt > _as_utc(assignment.start_datetime)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Data de encerramento deve ser posterior ao início da alocação.",
            )

        assignment.end_datetime = end_dt
        await db.flush()

        await record_audit_log(
            db=db,
            organization_id=org_id,
            actor_user_id=actor.user.id,
            action=AuditAction.UPDATE,
            entity_name="VehicleAssignment",
            entity_id=assignment.id,
            old_values={"end_datetime": None},
            new_values={"end_datetime": assignment.end_datetime.isoformat()},
        )
        return assignment

    @staticmethod
    async def delete_assignment(
        db: AsyncSession,
        actor: AuthContext,
        assignment_id: uuid.UUID,
    ) -> None:
        org_id = _require_org_id(actor)
        assignment = await OperationsService.get_assignment(db, actor, assignment_id)

        assignment.deleted_at = _utcnow()
        await db.flush()

        await record_audit_log(
            db=db,
            organization_id=org_id,
            actor_user_id=actor.user.id,
            action=AuditAction.DELETE,
            entity_name="VehicleAssignment",
            entity_id=assignment.id,
            old_values={
                "vehicle_id": str(assignment.vehicle_id),
                "driver_user_id": str(assignment.driver_user_id),
            },
        )

    @staticmethod
    async def upsert_financial_responsibility(
        db: AsyncSession,
        actor: AuthContext,
        payload: VehicleFinancialResponsibilityUpsert,
    ) -> VehicleFinancialResponsibility:
        org_id = _require_org_id(actor)
        await _assert_vehicle_in_org(db, org_id, payload.vehicle_id)

        existing = await db.scalar(
            select(VehicleFinancialResponsibility).where(
                VehicleFinancialResponsibility.vehicle_id == payload.vehicle_id,
                VehicleFinancialResponsibility.organization_id == org_id,
                VehicleFinancialResponsibility.expense_category == payload.expense_category,
            )
        )

        if existing is not None:
            old_values = {
                "default_payer_type": existing.default_payer_type,
                "default_economic_owner_type": existing.default_economic_owner_type,
            }
            existing.default_payer_type = payload.default_payer_type
            existing.default_economic_owner_type = payload.default_economic_owner_type
            await db.flush()

            await record_audit_log(
                db=db,
                organization_id=org_id,
                actor_user_id=actor.user.id,
                action=AuditAction.UPDATE,
                entity_name="VehicleFinancialResponsibility",
                entity_id=existing.id,
                old_values=old_values,
                new_values={
                    "expense_category": existing.expense_category,
                    "default_payer_type": existing.default_payer_type,
                    "default_economic_owner_type": existing.default_economic_owner_type,
                },
            )
            return existing

        rule = VehicleFinancialResponsibility(
            vehicle_id=payload.vehicle_id,
            organization_id=org_id,
            expense_category=payload.expense_category,
            default_payer_type=payload.default_payer_type,
            default_economic_owner_type=payload.default_economic_owner_type,
        )
        db.add(rule)
        await db.flush()

        await record_audit_log(
            db=db,
            organization_id=org_id,
            actor_user_id=actor.user.id,
            action=AuditAction.CREATE,
            entity_name="VehicleFinancialResponsibility",
            entity_id=rule.id,
            new_values={
                "vehicle_id": str(rule.vehicle_id),
                "expense_category": rule.expense_category,
                "default_payer_type": rule.default_payer_type,
                "default_economic_owner_type": rule.default_economic_owner_type,
            },
        )
        return rule

    @staticmethod
    async def list_financial_responsibilities(
        db: AsyncSession,
        actor: AuthContext,
        vehicle_id: Optional[uuid.UUID] = None,
    ) -> list[VehicleFinancialResponsibility]:
        org_id = _require_org_id(actor)
        conds = [VehicleFinancialResponsibility.organization_id == org_id]
        if vehicle_id is not None:
            await _assert_vehicle_in_org(db, org_id, vehicle_id)
            conds.append(VehicleFinancialResponsibility.vehicle_id == vehicle_id)

        stmt = (
            select(VehicleFinancialResponsibility)
            .where(*conds)
            .order_by(VehicleFinancialResponsibility.expense_category.asc())
        )
        return list((await db.scalars(stmt)).all())

    @staticmethod
    async def delete_financial_responsibility(
        db: AsyncSession,
        actor: AuthContext,
        responsibility_id: uuid.UUID,
    ) -> None:
        org_id = _require_org_id(actor)
        rule = await db.scalar(
            select(VehicleFinancialResponsibility).where(
                VehicleFinancialResponsibility.id == responsibility_id,
                VehicleFinancialResponsibility.organization_id == org_id,
            )
        )
        if rule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Regra de responsabilidade financeira não encontrada.",
            )

        old_values = {
            "vehicle_id": str(rule.vehicle_id),
            "expense_category": rule.expense_category,
            "default_payer_type": rule.default_payer_type,
            "default_economic_owner_type": rule.default_economic_owner_type,
        }
        await db.delete(rule)
        await db.flush()

        await record_audit_log(
            db=db,
            organization_id=org_id,
            actor_user_id=actor.user.id,
            action=AuditAction.DELETE,
            entity_name="VehicleFinancialResponsibility",
            entity_id=responsibility_id,
            old_values=old_values,
        )
