import uuid
from dataclasses import dataclass
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from jwt import PyJWKClient

from apps.api.app.core.config import settings
from apps.api.app.db.session import get_db
from manutcar_db.models.identity import User, Organization, OrganizationMember
from manutcar_db.models.fleet import Vehicle, VehicleManagementAgreement, VehicleAccessPermission
from manutcar_db.enums import OrgRole, AgreementStatus, VehicleOperationalStatus


# Clerk JWKS URL para validação de tokens RS256
CLERK_JWKS_URL = "https://clerk.your-domain.com/.well-known/jwks.json"  # Ajustar para o domínio real


def decode_clerk_jwt(token: str) -> dict:
    """
    Decodifica e valida um JWT do Clerk usando RS256 via JWKS.
    Valida claims básicos: exp, iat, sub.
    """
    jwk_client = PyJWKClient(CLERK_JWKS_URL)
    signing_key = jwk_client.get_signing_key_from_jwt(token)
    
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.CLERK_SECRET_KEY,  # Ou configurar audience apropriado
        options={"verify_aud": False},  # Ajustar conforme necessidade
    )
    
    # Validações básicas
    if "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: claim 'sub' ausente",
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
    clerk_org_id = payload.get("org_id")  # Pode vir no token se usuário estiver em uma org específica
    
    # Busca User ativo
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
    
    # Busca OrganizationMember ativo com Organization ativa
    # Se clerk_org_id veio no token, tenta filtrar por essa organização
    # Senão, prioriza personal workspace
    
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
        # Tenta converter clerk_org_id para UUID se for UUID válido
        # Senão, assume que é metadata/workspace e busca via Organization.clerk_org_id ou similar
        try:
            org_uuid = uuid.UUID(clerk_org_id)
            query = query.where(Organization.id == org_uuid)
        except ValueError:
            # Se não for UUID, pode ser um identificador do Clerk - ajustar conforme modelo
            # Assumindo que Organization tem campo clerk_org_id ou similar
            query = query.where(Organization.clerk_org_id == clerk_org_id)
    else:
        # Prioriza personal workspace
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
    # a) Busca Vehicle ativo
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
    
    # b) Verifica se current_owner pertence à organização
    # Assumindo que Vehicle tem relationship current_owner -> VehicleOwner
    # e VehicleOwner tem organization_id
    owner_org_match = False
    if vehicle.current_owner and vehicle.current_owner.organization_id == auth.organization.id:
        owner_org_match = True
    
    # Ou verifica VehicleManagementAgreement ativo
    agreement_result = await db.execute(
        select(VehicleManagementAgreement).where(
            VehicleManagementAgreement.vehicle_id == vehicle.id,
            VehicleManagementAgreement.organization_id == auth.organization.id,
            VehicleManagementAgreement.status == AgreementStatus.ACTIVE,
            VehicleManagementAgreement.deleted_at.is_(None),
        )
    )
    agreement = agreement_result.scalar_one_or_none()
    
    has_agreement = agreement is not None
    
    if not (owner_org_match or has_agreement):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organização não tem acesso a este veículo",
        )
    
    # c) Se required_permission informado, checa VehicleAccessPermission
    if required_permission and has_agreement:
        perm_result = await db.execute(
            select(VehicleAccessPermission).where(
                VehicleAccessPermission.agreement_id == agreement.id,
                VehicleAccessPermission.permission == required_permission,
            )
        )
        permission = perm_result.scalar_one_or_none()
        
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão '{required_permission}' não concedida para este veículo",
            )
    
    return vehicle
