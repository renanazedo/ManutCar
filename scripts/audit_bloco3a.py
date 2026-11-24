#!/usr/bin/env python3
"""
Script de auditoria determinística para validar o Bloco 3A.
Executa sem depender de servidor HTTP externo, usando mocks assíncronos precisos.
"""

import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Any
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

# Configura path para imports
sys.path.insert(0, "apps/api")

# =============================================================================
# 1. IMPORTS LIMPOS
# =============================================================================
try:
    from apps.api.app.core.config import settings
    from apps.api.app.db.session import get_db, AsyncSessionLocal, engine
    from apps.api.app.services.audit import record_audit_log
    from apps.api.app.core.security import (
        decode_clerk_jwt,
        get_current_auth_context,
        require_roles,
        verify_vehicle_access,
        AuthContext,
    )
    from manutcar_db.enums import OrgRole, AgreementStatus, AuditAction, VehicleOperationalStatus
    from manutcar_db.models.finance_audit import AuditLog
    from manutcar_db.models.identity import User, Organization, OrganizationMember
    from manutcar_db.models.fleet import Vehicle, VehicleOwner, VehicleManagementAgreement, VehicleAccessPermission
    print("✓ Imports limpos: config.py, session.py, audit.py, security.py")
except ImportError as e:
    print(f"✗ Falha nos imports: {e}")
    sys.exit(1)


# =============================================================================
# MOCKS E UTILITÁRIOS
# =============================================================================

class MockAsyncSession:
    """Mock assíncrono preciso do AsyncSession do SQLAlchemy."""
    
    def __init__(self):
        self.added_objects = []
        self.flushed = False
        self.committed = False
        self.rolled_back = False
        self._execute_results = []
        self._execute_index = 0
    
    def add(self, obj):
        self.added_objects.append(obj)
    
    async def flush(self):
        self.flushed = True
    
    async def commit(self):
        self.committed = True
    
    async def rollback(self):
        self.rolled_back = True
    
    async def close(self):
        pass
    
    def set_execute_results(self, results: List[Any]):
        """Define resultados sequenciais para chamadas de execute()."""
        self._execute_results = results
        self._execute_index = 0
    
    async def execute(self, query):
        if self._execute_index < len(self._execute_results):
            result = self._execute_results[self._execute_index]
            self._execute_index += 1
            return result
        # Retorna mock vazio por padrão
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.first.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        return mock_result
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


def create_mock_result(scalar_value=None, first_value=None):
    """Cria um mock de Result do SQLAlchemy."""
    mock = MagicMock()
    mock.scalar_one_or_none.return_value = scalar_value
    mock.first.return_value = first_value
    mock.scalars.return_value.all.return_value = []
    return mock


def create_user(
    id: uuid.UUID = None,
    clerk_user_id: str = "clerk_user_123",
    email: str = "test@example.com",
    is_anonymized: bool = False,
    deleted_at: Optional[datetime] = None,
) -> User:
    """Cria um User mock para testes."""
    user = MagicMock(spec=User)
    user.id = id or uuid.uuid4()
    user.clerk_user_id = clerk_user_id
    user.email = email
    user.is_anonymized = is_anonymized
    user.deleted_at = deleted_at
    return user


def create_organization(
    id: uuid.UUID = None,
    name: str = "Test Org",
    is_personal_workspace: bool = False,
    deleted_at: Optional[datetime] = None,
) -> Organization:
    """Cria uma Organization mock para testes."""
    org = MagicMock(spec=Organization)
    org.id = id or uuid.uuid4()
    org.name = name
    org.is_personal_workspace = is_personal_workspace
    org.deleted_at = deleted_at
    return org


def create_membership(
    id: uuid.UUID = None,
    user_id: uuid.UUID = None,
    organization_id: uuid.UUID = None,
    role: OrgRole = OrgRole.DRIVER,
    is_active: bool = True,
    deleted_at: Optional[datetime] = None,
) -> OrganizationMember:
    """Cria um OrganizationMember mock para testes."""
    member = MagicMock(spec=OrganizationMember)
    member.id = id or uuid.uuid4()
    member.user_id = user_id
    member.organization_id = organization_id
    member.role = role
    member.is_active = is_active
    member.deleted_at = deleted_at
    return member


def create_vehicle(
    id: uuid.UUID = None,
    plate: str = "ABC1D23",
    current_owner: VehicleOwner = None,
    deleted_at: Optional[datetime] = None,
) -> Vehicle:
    """Cria um Vehicle mock para testes."""
    vehicle = MagicMock(spec=Vehicle)
    vehicle.id = id or uuid.uuid4()
    vehicle.plate = plate
    vehicle.current_owner = current_owner
    vehicle.deleted_at = deleted_at
    vehicle.operational_status = VehicleOperationalStatus.ACTIVE
    return vehicle


def create_vehicle_owner(
    id: uuid.UUID = None,
    organization_id: uuid.UUID = None,
    user_id: uuid.UUID = None,
) -> VehicleOwner:
    """Cria um VehicleOwner mock para testes."""
    owner = MagicMock(spec=VehicleOwner)
    owner.id = id or uuid.uuid4()
    owner.organization_id = organization_id
    owner.user_id = user_id
    return owner


def create_agreement(
    id: uuid.UUID = None,
    vehicle_id: uuid.UUID = None,
    organization_id: uuid.UUID = None,
    status: AgreementStatus = AgreementStatus.ACTIVE,
    deleted_at: Optional[datetime] = None,
) -> VehicleManagementAgreement:
    """Cria um VehicleManagementAgreement mock para testes."""
    agreement = MagicMock(spec=VehicleManagementAgreement)
    agreement.id = id or uuid.uuid4()
    agreement.vehicle_id = vehicle_id
    agreement.organization_id = organization_id
    agreement.status = status
    agreement.deleted_at = deleted_at
    return agreement


def create_permission(
    agreement_id: uuid.UUID,
    permission: str = "view_maintenance",
) -> VehicleAccessPermission:
    """Cria um VehicleAccessPermission mock para testes."""
    perm = MagicMock(spec=VehicleAccessPermission)
    perm.agreement_id = agreement_id
    perm.permission = permission
    return perm


# =============================================================================
# TESTES
# =============================================================================

async def test_record_audit_log():
    """Testa record_audit_log: cria AuditLog, chama add/flush, não chama commit."""
    print("\n--- Teste 1: record_audit_log ---")
    
    db = MockAsyncSession()
    
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    
    log = await record_audit_log(
        db=db,
        organization_id=org_id,
        actor_user_id=actor_id,
        entity_name="Vehicle",
        entity_id=entity_id,
        action=AuditAction.CREATE,
        old_values=None,
        new_values={"plate": "ABC1D23"},
    )
    
    # Verificações
    assert isinstance(log, AuditLog), "Deve retornar instância de AuditLog"
    assert log.organization_id == org_id
    assert log.actor_user_id == actor_id
    assert log.entity_name == "Vehicle"
    assert log.entity_id == entity_id
    assert log.action == AuditAction.CREATE
    assert log.old_values is None
    assert log.new_values == {"plate": "ABC1D23"}
    
    assert len(db.added_objects) == 1, "Deve chamar db.add exatamente uma vez"
    assert db.added_objects[0] is log, "Objeto adicionado deve ser o log criado"
    
    assert db.flushed is True, "Deve chamar db.flush"
    assert db.committed is False, "NÃO deve chamar db.commit"
    
    print("✓ record_audit_log: cria AuditLog correto, chama add/flush, não chama commit")
    return True


async def test_get_current_auth_context_valid_token():
    """Testa get_current_auth_context com token válido."""
    print("\n--- Teste 2: get_current_auth_context (token válido) ---")
    
    # Setup
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    membership_id = uuid.uuid4()
    
    user = create_user(id=user_id, clerk_user_id="clerk_user_123")
    org = create_organization(id=org_id, name="Test Org")
    membership = create_membership(
        id=membership_id,
        user_id=user_id,
        organization_id=org_id,
        role=OrgRole.OWNER,
    )
    
    # Mock do decode_clerk_jwt
    with patch("apps.api.app.core.security.decode_clerk_jwt") as mock_decode:
        mock_decode.return_value = {
            "sub": "clerk_user_123",
            "org_id": str(org_id),
        }
        
        # Mock da sessão DB
        db = MockAsyncSession()
        # Primeira query: User
        # Segunda query: OrganizationMember + Organization
        db.set_execute_results([
            create_mock_result(scalar_value=user),
            create_mock_result(first_value=(membership, org)),
        ])
        
        # Mock do HTTPBearer credentials
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"
        
        # Executa
        auth = await get_current_auth_context(mock_credentials, db)
        
        # Verificações
        assert isinstance(auth, AuthContext), "Deve retornar AuthContext"
        assert auth.user is user
        assert auth.organization is org
        assert auth.membership is membership
        assert auth.clerk_user_id == "clerk_user_123"
        assert auth.clerk_org_id == str(org_id)
    
    print("✓ get_current_auth_context: retorna AuthContext com user, organization, membership")
    return True


async def test_get_current_auth_context_user_not_found():
    """Testa get_current_auth_context com usuário inexistente -> HTTP 401."""
    print("\n--- Teste 3: get_current_auth_context (usuário inexistente) ---")
    
    with patch("apps.api.app.core.security.decode_clerk_jwt") as mock_decode:
        mock_decode.return_value = {"sub": "clerk_user_inexistente"}
        
        db = MockAsyncSession()
        db.set_execute_results([
            create_mock_result(scalar_value=None),  # User não encontrado
        ])
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"
        
        try:
            await get_current_auth_context(mock_credentials, db)
            assert False, "Deveria ter levantado HTTPException 401"
        except Exception as e:
            assert hasattr(e, 'status_code'), "Deveria ser HTTPException"
            assert e.status_code == 401, f"Status code deve ser 401, got {e.status_code}"
            assert "não encontrado ou inativo" in str(e.detail)
    
    print("✓ get_current_auth_context: rejeita usuário inexistente com HTTP 401")
    return True


async def test_get_current_auth_context_user_anonymized():
    """Testa get_current_auth_context com usuário anonimizado -> HTTP 401."""
    print("\n--- Teste 4: get_current_auth_context (usuário anonimizado) ---")
    
    user = create_user(is_anonymized=True)
    
    with patch("apps.api.app.core.security.decode_clerk_jwt") as mock_decode:
        mock_decode.return_value = {"sub": "clerk_user_123"}
        
        db = MockAsyncSession()
        db.set_execute_results([
            create_mock_result(scalar_value=user),
        ])
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"
        
        try:
            await get_current_auth_context(mock_credentials, db)
            assert False, "Deveria ter levantado HTTPException 401"
        except Exception as e:
            assert e.status_code == 401
            assert "não encontrado ou inativo" in str(e.detail)
    
    print("✓ get_current_auth_context: rejeita usuário anonimizado com HTTP 401")
    return True


async def test_get_current_auth_context_no_membership():
    """Testa get_current_auth_context sem membership ativo -> HTTP 403."""
    print("\n--- Teste 5: get_current_auth_context (sem membership ativo) ---")
    
    user = create_user()
    
    with patch("apps.api.app.core.security.decode_clerk_jwt") as mock_decode:
        mock_decode.return_value = {"sub": "clerk_user_123", "org_id": "org_123"}
        
        db = MockAsyncSession()
        db.set_execute_results([
            create_mock_result(scalar_value=user),
            create_mock_result(first_value=None),  # Sem membership
        ])
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid_token"
        
        try:
            await get_current_auth_context(mock_credentials, db)
            assert False, "Deveria ter levantado HTTPException 403"
        except Exception as e:
            assert e.status_code == 403
            assert "não possui vínculo ativo" in str(e.detail)
    
    print("✓ get_current_auth_context: rejeita sem membership ativo com HTTP 403")
    return True


async def test_require_roles_allowed():
    """Testa require_roles com papel autorizado (OWNER)."""
    print("\n--- Teste 6: require_roles (papel autorizado) ---")
    
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    membership_id = uuid.uuid4()
    
    user = create_user(id=user_id)
    org = create_organization(id=org_id)
    membership = create_membership(
        id=membership_id,
        user_id=user_id,
        organization_id=org_id,
        role=OrgRole.OWNER,
    )
    
    auth = AuthContext(
        user=user,
        organization=org,
        membership=membership,
        clerk_user_id="clerk_123",
        clerk_org_id=str(org_id),
    )
    
    # Factory para OWNER
    checker = require_roles(OrgRole.OWNER, OrgRole.ADMIN)
    
    # Deve passar sem exceção
    result = await checker(auth)
    assert result is auth
    
    print("✓ require_roles: permite papel autorizado (OWNER)")
    return True


async def test_require_roles_denied():
    """Testa require_roles com papel não autorizado (DRIVER) -> HTTP 403."""
    print("\n--- Teste 7: require_roles (papel não autorizado) ---")
    
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    membership_id = uuid.uuid4()
    
    user = create_user(id=user_id)
    org = create_organization(id=org_id)
    membership = create_membership(
        id=membership_id,
        user_id=user_id,
        organization_id=org_id,
        role=OrgRole.DRIVER,
    )
    
    auth = AuthContext(
        user=user,
        organization=org,
        membership=membership,
        clerk_user_id="clerk_123",
        clerk_org_id=str(org_id),
    )
    
    # Factory apenas para OWNER
    checker = require_roles(OrgRole.OWNER)
    
    try:
        await checker(auth)
        assert False, "Deveria ter levantado HTTPException 403"
    except Exception as e:
        assert e.status_code == 403
        assert "Acesso restrito aos papéis" in str(e.detail)
        assert "OWNER" in str(e.detail)
    
    print("✓ require_roles: bloqueia papel não autorizado (DRIVER) com HTTP 403")
    return True


async def test_verify_vehicle_access_not_found():
    """Testa verify_vehicle_access com veículo inexistente -> HTTP 404."""
    print("\n--- Teste 8: verify_vehicle_access (veículo inexistente) ---")
    
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    vehicle_id = uuid.uuid4()
    
    user = create_user(id=user_id)
    org = create_organization(id=org_id)
    membership = create_membership(user_id=user_id, organization_id=org_id, role=OrgRole.OWNER)
    
    auth = AuthContext(
        user=user,
        organization=org,
        membership=membership,
        clerk_user_id="clerk_123",
        clerk_org_id=str(org_id),
    )
    
    db = MockAsyncSession()
    db.set_execute_results([
        create_mock_result(scalar_value=None),  # Vehicle não encontrado
    ])
    
    try:
        await verify_vehicle_access(db, auth, vehicle_id)
        assert False, "Deveria ter levantado HTTPException 404"
    except Exception as e:
        assert e.status_code == 404
        assert "não encontrado" in str(e.detail)
    
    print("✓ verify_vehicle_access: lança HTTP 404 para veículo inexistente")
    return True


async def test_verify_vehicle_access_owner_match():
    """Testa verify_vehicle_access com owner_org_match (current_owner.organization_id == auth.organization.id)."""
    print("\n--- Teste 9: verify_vehicle_access (owner_org_match) ---")
    
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    vehicle_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    
    user = create_user(id=user_id)
    org = create_organization(id=org_id)
    membership = create_membership(user_id=user_id, organization_id=org_id, role=OrgRole.OWNER)
    
    auth = AuthContext(
        user=user,
        organization=org,
        membership=membership,
        clerk_user_id="clerk_123",
        clerk_org_id=str(org_id),
    )
    
    # Vehicle com current_owner pertencente à mesma organização
    owner = create_vehicle_owner(id=owner_id, organization_id=org_id)
    vehicle = create_vehicle(id=vehicle_id, current_owner=owner)
    
    db = MockAsyncSession()
    db.set_execute_results([
        create_mock_result(scalar_value=vehicle),  # Vehicle encontrado
        create_mock_result(scalar_value=None),     # Sem agreement (não precisa)
    ])
    
    result = await verify_vehicle_access(db, auth, vehicle_id)
    assert result is vehicle
    
    print("✓ verify_vehicle_access: permite acesso quando current_owner.organization_id == auth.organization.id")
    return True


async def test_verify_vehicle_access_active_agreement():
    """Testa verify_vehicle_access com VehicleManagementAgreement ativo."""
    print("\n--- Teste 10: verify_vehicle_access (agreement ativo) ---")
    
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    vehicle_id = uuid.uuid4()
    agreement_id = uuid.uuid4()
    
    user = create_user(id=user_id)
    org = create_organization(id=org_id)
    membership = create_membership(user_id=user_id, organization_id=org_id, role=OrgRole.OWNER)
    
    auth = AuthContext(
        user=user,
        organization=org,
        membership=membership,
        clerk_user_id="clerk_123",
        clerk_org_id=str(org_id),
    )
    
    # Vehicle SEM current_owner da org, MAS com agreement ativo
    vehicle = create_vehicle(id=vehicle_id, current_owner=None)
    agreement = create_agreement(
        id=agreement_id,
        vehicle_id=vehicle_id,
        organization_id=org_id,
        status=AgreementStatus.ACTIVE,
    )
    
    db = MockAsyncSession()
    db.set_execute_results([
        create_mock_result(scalar_value=vehicle),      # Vehicle encontrado
        create_mock_result(scalar_value=agreement),    # Agreement ativo encontrado
    ])
    
    result = await verify_vehicle_access(db, auth, vehicle_id)
    assert result is vehicle
    
    print("✓ verify_vehicle_access: permite acesso quando existe Agreement ativo")
    return True


async def test_verify_vehicle_access_denied_no_owner_no_agreement():
    """Testa verify_vehicle_access bloqueia org externa sem propriedade nem contrato."""
    print("\n--- Teste 11: verify_vehicle_access (bloqueado - sem owner nem agreement) ---")
    
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    other_org_id = uuid.uuid4()
    vehicle_id = uuid.uuid4()
    
    user = create_user(id=user_id)
    org = create_organization(id=org_id)
    membership = create_membership(user_id=user_id, organization_id=org_id, role=OrgRole.OWNER)
    
    auth = AuthContext(
        user=user,
        organization=org,
        membership=membership,
        clerk_user_id="clerk_123",
        clerk_org_id=str(org_id),
    )
    
    # Vehicle pertence a OUTRA organização, sem agreement
    other_owner = create_vehicle_owner(organization_id=other_org_id)
    vehicle = create_vehicle(id=vehicle_id, current_owner=other_owner)
    
    db = MockAsyncSession()
    db.set_execute_results([
        create_mock_result(scalar_value=vehicle),   # Vehicle encontrado
        create_mock_result(scalar_value=None),      # Sem agreement
    ])
    
    try:
        await verify_vehicle_access(db, auth, vehicle_id)
        assert False, "Deveria ter levantado HTTPException 403"
    except Exception as e:
        assert e.status_code == 403
        assert "não tem acesso a este veículo" in str(e.detail)
    
    print("✓ verify_vehicle_access: bloqueia com HTTP 403 organização externa sem propriedade nem contrato ativo")
    return True


async def test_verify_vehicle_access_permission_required():
    """Testa verify_vehicle_access com required_permission."""
    print("\n--- Teste 12: verify_vehicle_access (com required_permission) ---")
    
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    vehicle_id = uuid.uuid4()
    agreement_id = uuid.uuid4()
    
    user = create_user(id=user_id)
    org = create_organization(id=org_id)
    membership = create_membership(user_id=user_id, organization_id=org_id, role=OrgRole.OWNER)
    
    auth = AuthContext(
        user=user,
        organization=org,
        membership=membership,
        clerk_user_id="clerk_123",
        clerk_org_id=str(org_id),
    )
    
    vehicle = create_vehicle(id=vehicle_id, current_owner=None)
    agreement = create_agreement(
        id=agreement_id,
        vehicle_id=vehicle_id,
        organization_id=org_id,
        status=AgreementStatus.ACTIVE,
    )
    permission = create_permission(agreement_id=agreement_id, permission="view_financial")
    
    db = MockAsyncSession()
    db.set_execute_results([
        create_mock_result(scalar_value=vehicle),      # Vehicle
        create_mock_result(scalar_value=agreement),    # Agreement
        create_mock_result(scalar_value=permission),   # Permission encontrada
    ])
    
    result = await verify_vehicle_access(db, auth, vehicle_id, required_permission="view_financial")
    assert result is vehicle
    
    print("✓ verify_vehicle_access: permite quando permission requerida existe")
    return True


async def test_verify_vehicle_access_permission_denied():
    """Testa verify_vehicle_access com required_permission não concedida."""
    print("\n--- Teste 13: verify_vehicle_access (permission negada) ---")
    
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    vehicle_id = uuid.uuid4()
    agreement_id = uuid.uuid4()
    
    user = create_user(id=user_id)
    org = create_organization(id=org_id)
    membership = create_membership(user_id=user_id, organization_id=org_id, role=OrgRole.OWNER)
    
    auth = AuthContext(
        user=user,
        organization=org,
        membership=membership,
        clerk_user_id="clerk_123",
        clerk_org_id=str(org_id),
    )
    
    vehicle = create_vehicle(id=vehicle_id, current_owner=None)
    agreement = create_agreement(
        id=agreement_id,
        vehicle_id=vehicle_id,
        organization_id=org_id,
        status=AgreementStatus.ACTIVE,
    )
    
    db = MockAsyncSession()
    db.set_execute_results([
        create_mock_result(scalar_value=vehicle),      # Vehicle
        create_mock_result(scalar_value=agreement),    # Agreement
        create_mock_result(scalar_value=None),         # Permission NÃO encontrada
    ])
    
    try:
        await verify_vehicle_access(db, auth, vehicle_id, required_permission="edit_financial")
        assert False, "Deveria ter levantado HTTPException 403"
    except Exception as e:
        assert e.status_code == 403
        assert "não concedida" in str(e.detail)
    
    print("✓ verify_vehicle_access: bloqueia quando permission requerida não existe")
    return True


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Executa todos os testes de auditoria."""
    print("=" * 70)
    print("AUDITORIA BLOCO 3A - Iniciando validações determinísticas")
    print("=" * 70)
    
    tests = [
        test_record_audit_log,
        test_get_current_auth_context_valid_token,
        test_get_current_auth_context_user_not_found,
        test_get_current_auth_context_user_anonymized,
        test_get_current_auth_context_no_membership,
        test_require_roles_allowed,
        test_require_roles_denied,
        test_verify_vehicle_access_not_found,
        test_verify_vehicle_access_owner_match,
        test_verify_vehicle_access_active_agreement,
        test_verify_vehicle_access_denied_no_owner_no_agreement,
        test_verify_vehicle_access_permission_required,
        test_verify_vehicle_access_permission_denied,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"✗ FALHA em {test_func.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"RESULTADO: {passed} passaram, {failed} falharam")
    print("=" * 70)
    
    if failed == 0:
        print("AUDITORIA_BLOCO3A_APROVADA")
        return 0
    else:
        print("AUDITORIA_BLOCO3A_REPROVADA")
        return 1


if __name__ == "__main__":
    exit_code = 0
    try:
        import asyncio
        exit_code = asyncio.run(main())
    except Exception as e:
        print(f"ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    
    sys.exit(exit_code)
