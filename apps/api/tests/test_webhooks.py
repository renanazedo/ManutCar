import uuid

import pytest
from apps.api.app.api.v1.endpoints.webhooks import verify_clerk_signature
from apps.api.app.main import app
from apps.api.app.services.sync_service import process_clerk_webhook
from fastapi import status
from manutcar_db.enums import OrgRole
from manutcar_db.models.finance_audit import AuditLog, ProcessedWebhookEvent
from manutcar_db.models.identity import (
    Organization,
    OrganizationMember,
    OrganizationSettings,
    User,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _user_payload(clerk_user_id: str) -> dict:
    return {
        "id": clerk_user_id,
        "email_addresses": [
            {"id": f"email_{clerk_user_id}", "email_address": "driver@example.com"}
        ],
        "phone_numbers": [],
        "first_name": "Test",
        "last_name": "Driver",
    }


def _organization_payload(clerk_organization_id: str) -> dict:
    return {
        "id": clerk_organization_id,
        "name": "Frota de Teste",
        "slug": "frota-de-teste",
    }


def _membership_payload(
    clerk_organization_id: str, clerk_user_id: str, role: str = "org:admin"
) -> dict:
    return {
        "id": "orgmem_test",
        "role": role,
        "organization": _organization_payload(clerk_organization_id),
        "public_user_data": {
            "user_id": clerk_user_id,
            "identifier": "driver@example.com",
        },
    }


@pytest.mark.asyncio
async def test_user_created_is_idempotent_and_creates_personal_workspace(
    db_session: AsyncSession,
):
    payload = _user_payload("user_clerk_test")

    async with db_session.begin():
        first = await process_clerk_webhook(
            db_session, "evt_user_created", "user.created", payload
        )
    async with db_session.begin():
        duplicate = await process_clerk_webhook(
            db_session, "evt_user_created", "user.created", payload
        )

    user = await db_session.scalar(
        select(User).where(User.clerk_user_id == "user_clerk_test")
    )
    orgs = list(
        (
            await db_session.scalars(
                select(Organization).where(
                    Organization.is_personal_workspace.is_(True),
                    Organization.members.any(OrganizationMember.user_id == user.id),
                )
            )
        ).all()
    )
    assert first["status"] == "processed"
    assert duplicate["status"] == "ignored_duplicate"
    assert len(orgs) == 1
    assert orgs[0].settings is not None
    member = await db_session.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == orgs[0].id,
            OrganizationMember.user_id == user.id,
        )
    )
    assert member is not None
    assert member.role == OrgRole.OWNER


@pytest.mark.asyncio
async def test_clerk_organization_and_membership_map_to_local_uuids(
    db_session: AsyncSession,
):
    clerk_user_id = "user_clerk_member"
    clerk_organization_id = "org_clerk_fleet"

    async with db_session.begin():
        await process_clerk_webhook(
            db_session,
            "evt_member_user",
            "user.created",
            _user_payload(clerk_user_id),
        )
    async with db_session.begin():
        await process_clerk_webhook(
            db_session,
            "evt_fleet_created",
            "organization.created",
            _organization_payload(clerk_organization_id),
        )
    async with db_session.begin():
        await process_clerk_webhook(
            db_session,
            "evt_membership_updated_first",
            "organizationMembership.updated",
            _membership_payload(clerk_organization_id, clerk_user_id, "org:member"),
        )
    async with db_session.begin():
        await process_clerk_webhook(
            db_session,
            "evt_membership_created",
            "organizationMembership.created",
            _membership_payload(clerk_organization_id, clerk_user_id),
        )

    org = await db_session.scalar(
        select(Organization).where(
            Organization.clerk_organization_id == clerk_organization_id
        )
    )
    user = await db_session.scalar(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    membership = await db_session.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user.id,
        )
    )
    settings = await db_session.scalar(
        select(OrganizationSettings).where(
            OrganizationSettings.organization_id == org.id
        )
    )
    assert isinstance(org.id, uuid.UUID)
    assert org.id != clerk_organization_id
    assert membership is not None
    assert membership.role == OrgRole.ADMIN
    assert settings is not None
    await db_session.commit()

    async with db_session.begin():
        await process_clerk_webhook(
            db_session,
            "evt_membership_deleted",
            "organizationMembership.deleted",
            _membership_payload(clerk_organization_id, clerk_user_id),
        )

    await db_session.refresh(membership)
    assert membership.is_active is False
    assert membership.deleted_at is not None
    await db_session.commit()

    async with db_session.begin():
        await process_clerk_webhook(
            db_session,
            "evt_membership_recreated",
            "organizationMembership.created",
            _membership_payload(clerk_organization_id, clerk_user_id),
        )

    await db_session.refresh(membership)
    assert membership.is_active is True
    assert membership.deleted_at is None


@pytest.mark.asyncio
async def test_user_updated_before_created_creates_personal_workspace(
    db_session: AsyncSession,
):
    async with db_session.begin():
        await process_clerk_webhook(
            db_session,
            "evt_user_updated_first",
            "user.updated",
            _user_payload("user_clerk_updated_first"),
        )

    user = await db_session.scalar(
        select(User).where(User.clerk_user_id == "user_clerk_updated_first")
    )
    personal_org_count = await db_session.scalar(
        select(func.count(Organization.id)).where(
            Organization.is_personal_workspace.is_(True),
            Organization.members.any(OrganizationMember.user_id == user.id),
        )
    )
    assert user is not None
    assert personal_org_count == 1


@pytest.mark.asyncio
async def test_membership_event_without_local_identity_returns_retryable_error(
    ac,
    db_session: AsyncSession,
):
    async def verified_payload():
        return {
            "type": "organizationMembership.created",
            "data": _membership_payload("org_not_synced", "user_not_synced"),
        }

    app.dependency_overrides[verify_clerk_signature] = verified_payload
    response = await ac.post(
        "/api/v1/webhooks/clerk",
        headers={"svix-id": "evt_membership_before_identity"},
        json={},
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    event = await db_session.scalar(
        select(ProcessedWebhookEvent).where(
            ProcessedWebhookEvent.event_id == "evt_membership_before_identity"
        )
    )
    assert event is None


@pytest.mark.asyncio
async def test_organization_updated_before_created_creates_local_mapping(
    db_session: AsyncSession,
):
    payload = _organization_payload("org_clerk_out_of_order")

    async with db_session.begin():
        await process_clerk_webhook(
            db_session,
            "evt_org_updated_first",
            "organization.updated",
            payload,
        )

    org = await db_session.scalar(
        select(Organization).where(
            Organization.clerk_organization_id == "org_clerk_out_of_order"
        )
    )
    audit_count = await db_session.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.entity_name == "Organization",
            AuditLog.entity_id == org.id,
        )
    )
    assert org is not None
    assert org.settings is not None
    assert audit_count == 1
