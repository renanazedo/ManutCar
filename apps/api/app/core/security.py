import uuid
from dataclasses import dataclass
from typing import Optional

import jwt
from apps.api.app.core.config import settings
from apps.api.app.db.session import get_db
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from manutcar_db.enums import AgreementStatus, OrgRole
from manutcar_db.models.fleet import (
    Vehicle,
    VehicleAccessPermission,
    VehicleManagementAgreement,
    VehicleOwner,
)
from manutcar_db.models.identity import Organization, OrganizationMember, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def decode_clerk_jwt(token: str) -> dict:
    """
    Valida um JWT do Clerk usando RS256, JWKS e as claims configuradas.
    """
    if not settings.CLERK_JWKS_URL or not settings.CLERK_JWT_ISSUER:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Autenticação Clerk não está configurada",
        )

    try:
        jwk_client = PyJWKClient(settings.CLERK_JWKS_URL)
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.CLERK_JWT_ISSUER,
            audience=settings.CLERK_JWT_AUDIENCE or None,
            options={
                "verify_aud": bool(settings.CLERK_JWT_AUDIENCE),
                "require": ["exp", "iat", "sub", "iss"],
            },
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        ) from exc

    if not isinstance(payload.get("sub"), str) or not payload["sub"].strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: claim 'sub' ausente",
        )
    if not settings.CLERK_JWT_AUDIENCE and payload.get("aud") is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token contém audience, mas CLERK_JWT_AUDIENCE não está configurada",
        )

    return payload


@dataclass
class AuthContext:
    user: User
    organization: Organization
    membership: OrganizationMember
    clerk_user_id: str
    clerk_org_id: Optional[str]


async def get_current_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """
    Dependency que valida o token Clerk, carrega User, Organization e OrganizationMember ativos.
    Implementa RN-FLT-01 para seleção de organização.
    """
    token = credentials.credentials
    payload = decode_clerk_jwt(token)

    clerk_user_id = payload.get("sub")
    clerk_org_id = payload.get("org_id")

    user_result = await db.execute(
        select(User).where(
            User.clerk_user_id == clerk_user_id,
            User.deleted_at.is_(None),
            User.is_anonymized.is_(False),
        )
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo",
        )

    query = (
        select(OrganizationMember, Organization)
        .join(Organization, OrganizationMember.organization_id == Organization.id)
        .where(
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_active.is_(True),
            OrganizationMember.deleted_at.is_(None),
            Organization.deleted_at.is_(None),
        )
    )

    if clerk_org_id:
        try:
            org_uuid = uuid.UUID(clerk_org_id)
            query = query.where(Organization.id == org_uuid)
        except ValueError:
            query = query.where(Organization.is_personal_workspace.is_(False))
    else:
        query = query.where(Organization.is_personal_workspace.is_(True))

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não possui vínculo ativo com a organização",
        )

    membership, organization = row

    return AuthContext(
        user=user,
        organization=organization,
        membership=membership,
        clerk_user_id=clerk_user_id,
        clerk_org_id=clerk_org_id,
    )


def require_roles(*allowed_roles: OrgRole):
    """
    Factory de dependency que verifica se o papel do membership está em allowed_roles.
    """

    async def role_checker(auth: AuthContext = Depends(get_current_auth_context)) -> AuthContext:
        if auth.membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso restrito aos papéis: {[r.value for r in allowed_roles]}",
            )
        return auth

    return role_checker


def _get_permission_column(permission: str):
    """Mapeia string de permissão para coluna booleana do VehicleAccessPermission."""
    permission_map = {
        "view_maintenance": VehicleAccessPermission.can_view_maintenance,
        "edit_maintenance": VehicleAccessPermission.can_edit_maintenance,
        "view_financial": VehicleAccessPermission.can_view_financial,
        "edit_financial": VehicleAccessPermission.can_edit_financial,
        "view_telemetry": VehicleAccessPermission.can_view_telemetry,
        "manage_drivers": VehicleAccessPermission.can_manage_drivers,
    }
    column = permission_map.get(permission)
    if column is None:
        raise ValueError(f"Permissão desconhecida: {permission}")
    return column


async def verify_vehicle_access(
    db: AsyncSession,
    auth: AuthContext,
    vehicle_id: uuid.UUID,
    required_permission: Optional[str] = None,
) -> Vehicle:
    """
    Verifica acesso a um veículo seguindo RN-FLT-01.
    a) Busca Vehicle ativo
    b) Permite se current_owner pertence à auth.organization OU existe VehicleManagementAgreement ativo
    c) Se required_permission informado, checa VehicleAccessPermission
    """
    vehicle_result = await db.execute(
        select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.deleted_at.is_(None),
        )
    )
    vehicle = vehicle_result.scalar_one_or_none()

    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veículo não encontrado",
        )

    owner_org_match = False
    if vehicle.current_owner and vehicle.current_owner.organization_id == auth.organization.id:
        owner_org_match = True

    if not owner_org_match:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organização não tem acesso a este veículo até a autorização granular estar disponível",
        )

    agreement_result = await db.execute(
        select(VehicleManagementAgreement)
        .join(VehicleOwner, VehicleManagementAgreement.owner_id == VehicleOwner.id)
        .where(
            VehicleManagementAgreement.vehicle_id == vehicle.id,
            VehicleManagementAgreement.organization_id == auth.organization.id,
            VehicleManagementAgreement.status == AgreementStatus.ACTIVE,
            VehicleManagementAgreement.deleted_at.is_(None),
            VehicleOwner.organization_id == auth.organization.id,
            VehicleOwner.deleted_at.is_(None),
        )
    )
    agreement = agreement_result.scalar_one_or_none()

    has_agreement = agreement is not None

    if required_permission and has_agreement:
        perm_column = _get_permission_column(required_permission)
        perm_result = await db.execute(
            select(VehicleAccessPermission).where(
                VehicleAccessPermission.agreement_id == agreement.id,
                perm_column.is_(True),
            )
        )
        permission = perm_result.scalar_one_or_none()

        if not permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão '{required_permission}' não concedida para este veículo",
            )

    return vehicle
