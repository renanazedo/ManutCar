"""
Serviço de Sincronização Clerk -> Banco Local.
Contém lógica de upsert para User, Organization, OrganizationMember.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from manutcar_db.models.identity import (
    User,
    Organization,
    OrganizationMember,
    OrganizationSettings,
)
from manutcar_db.models.finance_audit import ProcessedWebhookEvent
from manutcar_db.enums import OrgRole, AuditAction
from apps.api.app.services.audit import record_audit_log


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
        # 1. Cria Organization pessoal
        org_name = f"Minha Operação - {full_name or user.clerk_user_id[:8]}"
        org = Organization(
            name=org_name,
            is_personal_workspace=True,
        )
        db.add(org)
        await db.flush()

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

        # 3. Cria OrganizationMember como OWNER
        member = OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=OrgRole.OWNER,
            is_active=True,
        )
        db.add(member)

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

    if user and not user.is_anonymized:
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
    from packages.schemas.src.manutcar.schemas.webhook import ClerkUserData
    user_data = ClerkUserData(**data)

    existing_user = await db.execute(
        select(User).where(User.clerk_user_id == user_data.id)
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
        select(Organization).where(Organization.id == org_data.id)
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
    else:
        # Cria nova organização (não é workspace pessoal)
        org = Organization(
            id=org_data.id,
            name=org_data.name,
            document_number=org_data.slug if org_data.slug else None,  # Armazena slug/clerk_org_id em document_number se for CPF/CNPJ ou mantém name
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


async def _handle_org_updated(db: AsyncSession, data: dict):
    from packages.schemas.src.manutcar.schemas.webhook import ClerkOrganizationData
    org_data = ClerkOrganizationData(**data)

    existing_org = await db.execute(
        select(Organization).where(Organization.id == org_data.id)
    )
    org = existing_org.scalar_one_or_none()

    if org:
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


async def _handle_membership_created(db: AsyncSession, data: dict):
    from packages.schemas.src.manutcar.schemas.webhook import ClerkOrganizationMembershipData
    mem_data = ClerkOrganizationMembershipData(**data)

    # Mapeia role: 'admin' -> OrgRole.ADMIN, 'member' -> OrgRole.DRIVER
    role_map = {
        "admin": OrgRole.ADMIN,
        "member": OrgRole.DRIVER,
    }
    role = role_map.get(mem_data.role, OrgRole.DRIVER)

    existing_member = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == mem_data.organization.id,
            OrganizationMember.user_id == mem_data.public_user_data.user_id,
        )
    )
    member = existing_member.scalar_one_or_none()

    if member:
        # Atualiza membership existente
        old_values = {"role": member.role.value, "is_active": member.is_active}
        member.role = role
        member.is_active = True
        new_values = {"role": member.role.value, "is_active": member.is_active}
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
            organization_id=mem_data.organization.id,
            user_id=mem_data.public_user_data.user_id,
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

    role_map = {
        "admin": OrgRole.ADMIN,
        "member": OrgRole.DRIVER,
    }
    role = role_map.get(mem_data.role, OrgRole.DRIVER)

    existing_member = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == mem_data.organization.id,
            OrganizationMember.user_id == mem_data.public_user_data.user_id,
        )
    )
    member = existing_member.scalar_one_or_none()

    if member:
        old_values = {"role": member.role.value, "is_active": member.is_active}
        member.role = role
        member.is_active = True
        new_values = {"role": member.role.value, "is_active": member.is_active}
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


async def _handle_membership_deleted(db: AsyncSession, data: dict):
    from packages.schemas.src.manutcar.schemas.webhook import ClerkOrganizationMembershipData
    mem_data = ClerkOrganizationMembershipData(**data)

    existing_member = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == mem_data.organization.id,
            OrganizationMember.user_id == mem_data.public_user_data.user_id,
        )
    )
    member = existing_member.scalar_one_or_none()

    if member:
        old_values = {"is_active": member.is_active, "deleted_at": member.deleted_at}
        member.is_active = False
        member.deleted_at = datetime.now(timezone.utc)
        new_values = {"is_active": member.is_active, "deleted_at": member.deleted_at.isoformat() if member.deleted_at else None}
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
