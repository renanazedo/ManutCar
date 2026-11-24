"""
Serviço de Sincronização Clerk -> Banco Local.
Contém lógica de upsert para User, Organization, OrganizationMember.
"""
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from packages.db.src.manutcar.db.models import (
    User,
    Organization,
    OrganizationMember,
    OrganizationSettings,
)
from packages.schemas.src.manutcar.schemas.webhook import (
    ClerkUserData,
    ClerkOrganizationData,
    ClerkMembershipData,
)


async def sync_clerk_event(db: AsyncSession, event_type: str, data: dict):
    """
    Dispatcher principal. Chama handlers específicos por tipo de evento.
    """
    handlers = {
        "user.created": _handle_user_created,
        "user.updated": _handle_user_updated,
        "user.deleted": _handle_user_deleted,
        "organization.created": _handle_org_created,
        "organization.updated": _handle_org_updated,
        "organization.deleted": _handle_org_deleted,
        "organizationMembership.created": _handle_membership_created,
        "organizationMembership.updated": _handle_membership_updated,
        "organizationMembership.deleted": _handle_membership_deleted,
    }

    handler = handlers.get(event_type)
    if handler:
        await handler(db, data)
    else:
        # Evento não tratado (ex: session.created, email.created) - apenas loga
        print(f"Webhook Clerk: Evento não tratado '{event_type}'")


# --- Handlers ---

async def _handle_user_created(db: AsyncSession, data: dict):
    user_data = ClerkUserData(**data)
    # Upsert User
    stmt = pg_insert(User).values(
        id=user_data.id,
        auth_provider_id=user_data.id, # Clerk User ID
        email=user_data.email_addresses[0].email_address if user_data.email_addresses else None,
        full_name=f"{user_data.first_name or ''} {user_data.last_name or ''}".strip() or None,
        avatar_url=user_data.image_url,
        phone=user_data.phone_numbers[0].phone_number if user_data.phone_numbers else None,
        status="ACTIVE",
        role_global="DRIVER", # Default, pode mudar via convite
        metadata_json=user_data.unsafe_metadata or {},
    )
    # On conflict do PK (id) -> update campos mutáveis
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "email": stmt.excluded.email,
            "full_name": stmt.excluded.full_name,
            "avatar_url": stmt.excluded.avatar_url,
            "phone": stmt.excluded.phone,
            "metadata_json": stmt.excluded.metadata_json,
        },
    )
    await db.execute(stmt)

    # DEC-009: Criar Organização Pessoal ("Minha Operação") automaticamente
    # Verifica se já existe org com owner_id = user_id
    res = await db.execute(select(Organization).where(Organization.owner_user_id == user_data.id))
    if not res.scalar_one_or_none():
        org = Organization(
            name=f"Minha Operação - {user_data.first_name or user_data.id[:8]}",
            slug=f"pessoal-{user_data.id}",
            owner_user_id=user_data.id,
            settings=OrganizationSettings(), # Defaults
        )
        db.add(org)
        await db.flush() # Para ter org.id

        # Vincular user como ADMIN da org pessoal
        member = OrganizationMember(
            organization_id=org.id,
            user_id=user_data.id,
            role="ADMIN",
            status="ACTIVE",
        )
        db.add(member)


async def _handle_user_updated(db: AsyncSession, data: dict):
    user_data = ClerkUserData(**data)
    stmt = pg_insert(User).values(
        id=user_data.id,
        email=user_data.email_addresses[0].email_address if user_data.email_addresses else None,
        full_name=f"{user_data.first_name or ''} {user_data.last_name or ''}".strip() or None,
        avatar_url=user_data.image_url,
        phone=user_data.phone_numbers[0].phone_number if user_data.phone_numbers else None,
        metadata_json=user_data.unsafe_metadata or {},
    ).on_conflict_do_update(
        index_elements=["id"],
        set_={
            "email": stmt.excluded.email,
            "full_name": stmt.excluded.full_name,
            "avatar_url": stmt.excluded.avatar_url,
            "phone": stmt.excluded.phone,
            "metadata_json": stmt.excluded.metadata_json,
        },
    )
    await db.execute(stmt)


async def _handle_user_deleted(db: AsyncSession, data: dict):
    # Soft Delete (LGPD/Anonimização futura)
    user_id = data.get("id")
    if user_id:
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                status="DELETED",
                deleted_at=datetime.now(timezone.utc),
                email=f"deleted_{user_id}@manutcar.local", # Anonimização básica imediata
                full_name="Usuário Removido",
            )
        )


async def _handle_org_created(db: AsyncSession, data: dict):
    org_data = ClerkOrganizationData(**data)
    stmt = pg_insert(Organization).values(
        id=org_data.id,
        name=org_data.name,
        slug=org_data.slug,
        owner_user_id=org_data.created_by, # Quem criou no Clerk
        settings=OrganizationSettings(),
    ).on_conflict_do_update(
        index_elements=["id"],
        set_={"name": stmt.excluded.name, "slug": stmt.excluded.slug},
    )
    await db.execute(stmt)


async def _handle_org_updated(db: AsyncSession, data: dict):
    org_data = ClerkOrganizationData(**data)
    stmt = pg_insert(Organization).values(
        id=org_data.id,
        name=org_data.name,
        slug=org_data.slug,
    ).on_conflict_do_update(
        index_elements=["id"],
        set_={"name": stmt.excluded.name, "slug": stmt.excluded.slug},
    )
    await db.execute(stmt)


async def _handle_org_deleted(db: AsyncSession, data: dict):
    org_id = data.get("id")
    if org_id:
        await db.execute(
            update(Organization)
            .where(Organization.id == org_id)
            .values(deleted_at=datetime.now(timezone.utc), status="DELETED")
        )


async def _handle_membership_created(db: AsyncSession, data: dict):
    mem_data = ClerkMembershipData(**data)
    # Role mapping: Clerk 'admin' -> 'ADMIN', 'member' -> 'MEMBER' (ou DRIVER/GESTOR conforme convite)
    role_map = {"admin": "ADMIN", "member": "MEMBER"}
    role = role_map.get(mem_data.role, "MEMBER")

    stmt = pg_insert(OrganizationMember).values(
        organization_id=mem_data.organization.id,
        user_id=mem_data.public_user_data.user_id,
        role=role,
        status="ACTIVE",
    ).on_conflict_do_update(
        index_elements=["organization_id", "user_id"],
        set_={"role": stmt.excluded.role, "status": "ACTIVE"},
    )
    await db.execute(stmt)


async def _handle_membership_updated(db: AsyncSession, data: dict):
    mem_data = ClerkMembershipData(**data)
    role_map = {"admin": "ADMIN", "member": "MEMBER"}
    role = role_map.get(mem_data.role, "MEMBER")

    await db.execute(
        update(OrganizationMember)
        .where(
            OrganizationMember.organization_id == mem_data.organization.id,
            OrganizationMember.user_id == mem_data.public_user_data.user_id,
        )
        .values(role=role, status="ACTIVE")
    )


async def _handle_membership_deleted(db: AsyncSession, data: dict):
    mem_data = ClerkMembershipData(**data)
    await db.execute(
        update(OrganizationMember)
        .where(
            OrganizationMember.organization_id == mem_data.organization.id,
            OrganizationMember.user_id == mem_data.public_user_data.user_id,
        )
        .values(status="REMOVED", deleted_at=datetime.now(timezone.utc))
    )
