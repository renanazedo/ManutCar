"""
Serviço de Sincronização Clerk -> Banco Local.
Contém lógica de upsert para User, Organization, OrganizationMember.
"""
import uuid
from datetime import datetime, timezone

from apps.api.app.services.audit import record_audit_log
from fastapi import HTTPException, status
from manutcar_db.enums import AuditAction, OrgRole
from manutcar_db.models.finance_audit import ProcessedWebhookEvent
from manutcar_db.models.identity import (
    Organization,
    OrganizationMember,
    OrganizationSettings,
    User,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def process_clerk_webhook(db: AsyncSession, event_id: str, event_type: str, data: dict) -> dict:
    """
    Processa evento do Clerk com idempotência via ProcessedWebhookEvent.
    Retorna dict com status do processamento.
    """
    # a) Idempotência: consulta ProcessedWebhookEvent onde event_id == event_id
    existing = await db.execute(
        select(ProcessedWebhookEvent).where(ProcessedWebhookEvent.event_id == event_id)
    )
    if existing.scalar_one_or_none():
        return {"status": "ignored_duplicate", "event_id": event_id}

    # Registra ProcessedWebhookEvent
    processed_event = ProcessedWebhookEvent(event_id=event_id, provider="clerk")
    db.add(processed_event)
    await db.flush()

    # Dispatch para handlers
    handlers = {
        "user.created": _handle_user_created,
        "user.updated": _handle_user_updated,
        "user.deleted": _handle_user_deleted,
        "organization.created": _handle_org_created,
        "organization.updated": _handle_org_updated,
        "organizationMembership.created": _handle_membership_created,
        "organizationMembership.updated": _handle_membership_updated,
        "organizationMembership.deleted": _handle_membership_deleted,
    }

    handler = handlers.get(event_type)
    if handler:
        await handler(db, data)
    else:
        # Evento não tratado - apenas loga
        print(f"Webhook Clerk: Evento não tratado '{event_type}'")

    return {"status": "processed", "event_id": event_id, "event_type": event_type}


# --- Handlers ---

async def _handle_user_created(db: AsyncSession, data: dict):
    from packages.schemas.src.manutcar.schemas.webhook import ClerkUserData
    user_data = ClerkUserData(**data)

    # Upsert/criação de User buscando por clerk_user_id
    existing_user = await db.execute(
        select(User).where(User.clerk_user_id == user_data.id)
    )
    user = existing_user.scalar_one_or_none()

    email = user_data.email_addresses[0].email_address if user_data.email_addresses else None
    full_name = f"{user_data.first_name or ''} {user_data.last_name or ''}".strip() or None
    phone = user_data.phone_numbers[0].phone_number if user_data.phone_numbers else None

    if user:
        # Atualiza usuário existente
        old_values = {
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
        }
        user.email = email
        user.full_name = full_name
        user.phone = phone
        new_values = {
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
        }
        await record_audit_log(
            db,
            organization_id=None,
            actor_user_id=None,
            entity_name="User",
            entity_id=user.id,
            action=AuditAction.UPDATE,
            old_values=old_values,
            new_values=new_values,
        )
    else:
        # Cria novo usuário
        user = User(
            id=uuid.uuid4(),
            clerk_user_id=user_data.id,
            email=email,
            full_name=full_name,
            phone=phone,
            is_anonymized=False,
        )
        db.add(user)
        await db.flush()

        await record_audit_log(
            db,
            organization_id=None,
            actor_user_id=None,
            entity_name="User",
            entity_id=user.id,
            action=AuditAction.CREATE,
            old_values=None,
            new_values={
                "clerk_user_id": user.clerk_user_id,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
            },
        )

    # Onboarding Automático: verifica se usuário já possui Organization com is_personal_workspace=True
    personal_org = await db.execute(
        select(Organization).where(
            Organization.is_personal_workspace.is_(True),
            Organization.members.any(OrganizationMember.user_id == user.id)
        )
    )
    if not personal_org.scalar_one_or_none():
        # 1. Cria Organization pessoal COM ID EXPLÍCITO
        org_name = f"Minha Operação - {full_name or user.clerk_user_id[:8]}"
        org = Organization(
            id=uuid.uuid4(),  # ID explícito para garantir que não seja None no AuditLog
            name=org_name,
            is_personal_workspace=True,
        )
        db.add(org)
        await db.flush()  # Garante que org.id está populado

        await record_audit_log(
            db,
            organization_id=org.id,
            actor_user_id=user.id,
            entity_name="Organization",
            entity_id=org.id,
            action=AuditAction.CREATE,
            old_values=None,
            new_values={"name": org.name, "is_personal_workspace": True},
        )

        # 2. Cria OrganizationSettings com defaults
        settings = OrganizationSettings(organization_id=org.id)
        db.add(settings)

        # 3. Cria OrganizationMember como OWNER COM ID EXPLÍCITO
        member = OrganizationMember(
            id=uuid.uuid4(),  # ID explícito para garantir que não seja None no AuditLog
            organization_id=org.id,
            user_id=user.id,
            role=OrgRole.OWNER,
            is_active=True,
        )
        db.add(member)
        await db.flush()  # Garante que member.id está populado

        await record_audit_log(
            db,
            organization_id=org.id,
            actor_user_id=user.id,
            entity_name="OrganizationMember",
            entity_id=member.id,
            action=AuditAction.CREATE,
            old_values=None,
            new_values={"role": OrgRole.OWNER.value, "is_active": True},
        )


async def _handle_user_updated(db: AsyncSession, data: dict):
    from packages.schemas.src.manutcar.schemas.webhook import ClerkUserData
    user_data = ClerkUserData(**data)

    existing_user = await db.execute(
        select(User).where(User.clerk_user_id == user_data.id)
    )
    user = existing_user.scalar_one_or_none()

    if user is None:
        await _handle_user_created(db, data)
        return

    if user.is_anonymized:
        return

    old_values = {
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
    }
    email = user_data.email_addresses[0].email_address if user_data.email_addresses else None
    full_name = f"{user_data.first_name or ''} {user_data.last_name or ''}".strip() or None
    phone = user_data.phone_numbers[0].phone_number if user_data.phone_numbers else None

    user.email = email
    user.full_name = full_name
    user.phone = phone

    new_values = {
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
    }
    await record_audit_log(
        db,
        organization_id=None,
        actor_user_id=None,
        entity_name="User",
        entity_id=user.id,
        action=AuditAction.UPDATE,
        old_values=old_values,
        new_values=new_values,
    )


async def _handle_user_deleted(db: AsyncSession, data: dict):
    # No evento user.deleted, o Clerk envia apenas {"id": "...", "deleted": true}
    # Extraímos o clerk_user_id diretamente do campo "id" do data
    clerk_user_id = data.get("id")
    
    if not clerk_user_id:
        print("Webhook Clerk user.deleted: campo 'id' ausente no payload")
        return

    existing_user = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    user = existing_user.scalar_one_or_none()

    if user:
        # Anonimização Irreversível LGPD (RN-AUD-03)
        old_values = {
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "is_anonymized": user.is_anonymized,
        }

        user.is_anonymized = True
        user.deleted_at = datetime.now(timezone.utc)
        user.email = f"anon_{user.id}@deleted.manutcar.local"
        user.full_name = "Usuário Anonimizado"
        user.phone = None

        # Desativa memberships
        memberships = await db.execute(
            select(OrganizationMember).where(OrganizationMember.user_id == user.id)
        )
        for membership in memberships.scalars().all():
            membership.is_active = False
            membership.deleted_at = datetime.now(timezone.utc)

        new_values = {
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "is_anonymized": user.is_anonymized,
            "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
        }
        await record_audit_log(
            db,
            organization_id=None,
            actor_user_id=None,
            entity_name="User",
            entity_id=user.id,
            action=AuditAction.DELETE,
            old_values=old_values,
            new_values=new_values,
        )


async def _handle_org_created(db: AsyncSession, data: dict):
    from packages.schemas.src.manutcar.schemas.webhook import ClerkOrganizationData
    org_data = ClerkOrganizationData(**data)

    existing_org = await db.execute(
        select(Organization).where(
            Organization.clerk_organization_id == org_data.id
        )
    )
    org = existing_org.scalar_one_or_none()

    if org:
        # Atualiza organização existente
        old_values = {"name": org.name}
        org.name = org_data.name
        new_values = {"name": org.name}
        await record_audit_log(
            db,
            organization_id=org.id,
            actor_user_id=None,
            entity_name="Organization",
            entity_id=org.id,
            action=AuditAction.UPDATE,
            old_values=old_values,
            new_values=new_values,
        )
        if org.settings is None:
            db.add(OrganizationSettings(organization_id=org.id))
    else:
        org = Organization(
            clerk_organization_id=org_data.id,
            name=org_data.name,
            is_personal_workspace=False,
        )
        db.add(org)
        await db.flush()

        await record_audit_log(
            db,
            organization_id=org.id,
            actor_user_id=None,
            entity_name="Organization",
            entity_id=org.id,
            action=AuditAction.CREATE,
            old_values=None,
            new_values={"name": org.name, "is_personal_workspace": False},
        )
        db.add(OrganizationSettings(organization_id=org.id))


async def _handle_org_updated(db: AsyncSession, data: dict):
    from packages.schemas.src.manutcar.schemas.webhook import ClerkOrganizationData
    org_data = ClerkOrganizationData(**data)

    existing_org = await db.execute(
        select(Organization).where(
            Organization.clerk_organization_id == org_data.id
        )
    )
    org = existing_org.scalar_one_or_none()

    if org is None:
        await _handle_org_created(db, data)
        return

    old_values = {"name": org.name}
    org.name = org_data.name
    new_values = {"name": org.name}
    await record_audit_log(
        db,
        organization_id=org.id,
        actor_user_id=None,
        entity_name="Organization",
        entity_id=org.id,
        action=AuditAction.UPDATE,
        old_values=old_values,
        new_values=new_values,
    )


async def _resolve_membership_entities(
    db: AsyncSession, organization_id: str, user_id: str
) -> tuple[Organization, User]:
    org = await db.scalar(
        select(Organization).where(
            Organization.clerk_organization_id == organization_id
        )
    )
    user = await db.scalar(select(User).where(User.clerk_user_id == user_id))
    if org is None or user is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Clerk organization or user has not been synchronized locally; "
                "retry this webhook."
            ),
        )
    return org, user


def _map_clerk_membership_role(role: str) -> OrgRole:
    role_map = {
        "admin": OrgRole.ADMIN,
        "org:admin": OrgRole.ADMIN,
        "member": OrgRole.DRIVER,
        "org:member": OrgRole.DRIVER,
    }
    return role_map.get(role, OrgRole.DRIVER)


async def _handle_membership_created(db: AsyncSession, data: dict):
    from packages.schemas.src.manutcar.schemas.webhook import ClerkOrganizationMembershipData
    mem_data = ClerkOrganizationMembershipData(**data)

    org, user = await _resolve_membership_entities(
        db,
        mem_data.organization.id,
        mem_data.public_user_data.user_id,
    )
    role = _map_clerk_membership_role(mem_data.role)

    existing_member = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user.id,
        )
    )
    member = existing_member.scalar_one_or_none()

    if member:
        # Atualiza membership existente
        old_values = {
            "role": member.role.value,
            "is_active": member.is_active,
            "deleted_at": member.deleted_at.isoformat() if member.deleted_at else None,
        }
        member.role = role
        member.is_active = True
        member.deleted_at = None
        new_values = {
            "role": member.role.value,
            "is_active": member.is_active,
            "deleted_at": None,
        }
        await record_audit_log(
            db,
            organization_id=member.organization_id,
            actor_user_id=None,
            entity_name="OrganizationMember",
            entity_id=member.id,
            action=AuditAction.UPDATE,
            old_values=old_values,
            new_values=new_values,
        )
    else:
        # Cria novo membership
        member = OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=role,
            is_active=True,
        )
        db.add(member)
        await db.flush()

        await record_audit_log(
            db,
            organization_id=member.organization_id,
            actor_user_id=None,
            entity_name="OrganizationMember",
            entity_id=member.id,
            action=AuditAction.CREATE,
            old_values=None,
            new_values={"role": member.role.value, "is_active": member.is_active},
        )


async def _handle_membership_updated(db: AsyncSession, data: dict):
    from packages.schemas.src.manutcar.schemas.webhook import ClerkOrganizationMembershipData
    mem_data = ClerkOrganizationMembershipData(**data)

    org, user = await _resolve_membership_entities(
        db,
        mem_data.organization.id,
        mem_data.public_user_data.user_id,
    )
    role = _map_clerk_membership_role(mem_data.role)

    existing_member = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user.id,
        )
    )
    member = existing_member.scalar_one_or_none()

    if member:
        old_values = {
            "role": member.role.value,
            "is_active": member.is_active,
            "deleted_at": member.deleted_at.isoformat() if member.deleted_at else None,
        }
        member.role = role
        member.is_active = True
        member.deleted_at = None
        new_values = {
            "role": member.role.value,
            "is_active": member.is_active,
            "deleted_at": None,
        }
        await record_audit_log(
            db,
            organization_id=member.organization_id,
            actor_user_id=None,
            entity_name="OrganizationMember",
            entity_id=member.id,
            action=AuditAction.UPDATE,
            old_values=old_values,
            new_values=new_values,
        )
    else:
        await _handle_membership_created(db, data)


async def _handle_membership_deleted(db: AsyncSession, data: dict):
    from packages.schemas.src.manutcar.schemas.webhook import ClerkOrganizationMembershipData
    mem_data = ClerkOrganizationMembershipData(**data)
    org, user = await _resolve_membership_entities(
        db,
        mem_data.organization.id,
        mem_data.public_user_data.user_id,
    )

    existing_member = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user.id,
        )
    )
    member = existing_member.scalar_one_or_none()

    if member:
        if not member.is_active and member.deleted_at is not None:
            return

        old_values = {
            "is_active": member.is_active,
            "deleted_at": member.deleted_at.isoformat() if member.deleted_at else None,
        }
        member.is_active = False
        member.deleted_at = datetime.now(timezone.utc)
        new_values = {
            "is_active": member.is_active,
            "deleted_at": member.deleted_at.isoformat(),
        }
        await record_audit_log(
            db,
            organization_id=member.organization_id,
            actor_user_id=None,
            entity_name="OrganizationMember",
            entity_id=member.id,
            action=AuditAction.UPDATE,
            old_values=old_values,
            new_values=new_values,
        )
