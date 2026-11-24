#!/usr/bin/env python3
"""
Script de auditoria determinística para validar o Bloco 3B.
Executa sem depender de servidor HTTP externo, usando mocks assíncronos precisos.
Valida: idempotência, onboarding automático, anonimização LGPD, verificação de assinatura Svix.
"""

import sys
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

# Configurações obrigatórias no topo
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("CLERK_WEBHOOK_SECRET", "whsec_test_secret_123456789012345678901234")
os.environ.setdefault("CLERK_JWKS_URL", "https://clerk.test/.well-known/jwks.json")
os.environ.setdefault("CLERK_SECRET_KEY", "sk_test_123")

# =============================================================================
# 1. IMPORTS LIMPOS
# =============================================================================
try:
    from apps.api.app.services.sync_service import process_clerk_webhook
    from apps.api.app.api.v1.endpoints.webhooks import verify_clerk_signature, clerk_webhook
    from apps.api.app.api.v1.router import api_router
    from packages.schemas.src.manutcar.schemas.webhook import (
        ClerkUserData,
        ClerkOrganizationData,
        ClerkOrganizationMembershipData,
        ClerkWebhookPayload,
    )
    from manutcar_db.enums import OrgRole, AuditAction
    from manutcar_db.models.finance_audit import ProcessedWebhookEvent, AuditLog
    from manutcar_db.models.identity import User, Organization, OrganizationMember, OrganizationSettings
    print("✓ Imports limpos: sync_service.py, webhooks.py, router.py, webhook.py (schemas)")
except ImportError as e:
    print(f"✗ Falha nos imports: {e}")
    import traceback
    traceback.print_exc()
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
        self._scalars_results = {}
    
    def add(self, obj):
        self.added_objects.append(obj)
    
    async def flush(self):
        self.flushed = True
        # Simula geração de IDs para objetos sem ID
        for obj in self.added_objects:
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = uuid.uuid4()
    
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
        
        # Mock padrão baseado no tipo de query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.first.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        return mock_result
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


def create_mock_result(scalar_value=None, first_value=None, scalars_all=None):
    """Cria um mock de Result do SQLAlchemy."""
    mock = MagicMock()
    mock.scalar_one_or_none.return_value = scalar_value
    mock.first.return_value = first_value
    mock.scalars.return_value.all.return_value = scalars_all or []
    return mock


def create_user(
    id: uuid.UUID = None,
    clerk_user_id: str = "clerk_user_123",
    email: str = "test@example.com",
    full_name: str = "Test User",
    phone: str = "+5511999999999",
    is_anonymized: bool = False,
    deleted_at: Optional[datetime] = None,
) -> User:
    """Cria um User mock para testes."""
    user = MagicMock(spec=User)
    user.id = id or uuid.uuid4()
    user.clerk_user_id = clerk_user_id
    user.email = email
    user.full_name = full_name
    user.phone = phone
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


def create_settings(organization_id: uuid.UUID) -> OrganizationSettings:
    """Cria OrganizationSettings mock."""
    settings = MagicMock(spec=OrganizationSettings)
    settings.organization_id = organization_id
    return settings


# =============================================================================
# TESTES
# =============================================================================

async def test_imports_and_router():
    print("--- Teste 1: Imports e validacao de rota ---")
    from apps.api.app.main import app as _fastapi_app
    routes = [getattr(route, "path", "") for route in _fastapi_app.routes]
    webhook_routes = [r for r in routes if "webhooks" in r]
    assert "/api/v1/webhooks/clerk" in webhook_routes, f"Rota /api/v1/webhooks/clerk nao encontrada. Rotas: {routes}"
    assert "/api/v1/webhooks/webhooks/clerk" not in webhook_routes, "Duplicacao de prefixo detectada"
    print("OK: Rota /api/v1/webhooks/clerk registrada corretamente sem duplicacao de prefixo")
    return True


async def test_user_created_onboarding():
    """Testa process_clerk_webhook com user.created: cria User, Organization, Settings, Member, ProcessedWebhookEvent e 3 AuditLogs."""
    print("\n--- Teste 2: user.created com Onboarding Automático ---")
    
    db = MockAsyncSession()
    
    # Mock: User não existe, Organization pessoal não existe
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    member_id = uuid.uuid4()
    
    # Simula que não existe ProcessedWebhookEvent (idempotência)
    # Simula que não existe User
    # Simula que não existe Organization pessoal
    db.set_execute_results([
        create_mock_result(scalar_value=None),  # ProcessedWebhookEvent não existe
        create_mock_result(scalar_value=None),  # User não existe
        create_mock_result(scalar_value=None),  # Organization pessoal não existe
    ])
    
    # Payload user.created
    event_id = "msg_test_001"
    event_type = "user.created"
    data = {
        "id": "clerk_user_123",
        "email_addresses": [{"id": "email_1", "email_address": "test@example.com", "verification": {}}],
        "phone_numbers": [{"id": "phone_1", "phone_number": "+5511999999999", "verification": {}}],
        "first_name": "Test",
        "last_name": "User",
        "unsafe_metadata": {},
        "public_metadata": {},
    }
    
    result = await process_clerk_webhook(db, event_id, event_type, data)
    
    # Verificações
    assert result["status"] == "processed", f"Status esperado 'processed', got {result['status']}"
    assert result["event_id"] == event_id
    assert result["event_type"] == event_type
    
    # Verifica se ProcessedWebhookEvent foi criado
    processed_events = [obj for obj in db.added_objects if isinstance(obj, ProcessedWebhookEvent)]
    assert len(processed_events) == 1, "Deve criar exatamente 1 ProcessedWebhookEvent"
    assert processed_events[0].event_id == event_id
    assert processed_events[0].provider == "clerk"
    
    # Verifica se User foi criado
    users = [obj for obj in db.added_objects if isinstance(obj, User)]
    assert len(users) == 1, "Deve criar exatamente 1 User"
    user = users[0]
    assert user.clerk_user_id == "clerk_user_123"
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    
    # Verifica se Organization pessoal foi criada
    orgs = [obj for obj in db.added_objects if isinstance(obj, Organization)]
    assert len(orgs) == 1, "Deve criar exatamente 1 Organization (pessoal)"
    org = orgs[0]
    assert org.is_personal_workspace is True
    assert org.id is not None, "Organization.id não deve ser None"
    
    # Verifica se OrganizationSettings foi criada
    settings = [obj for obj in db.added_objects if isinstance(obj, OrganizationSettings)]
    assert len(settings) == 1, "Deve criar exatamente 1 OrganizationSettings"
    assert settings[0].organization_id == org.id
    
    # Verifica se OrganizationMember foi criado como OWNER
    members = [obj for obj in db.added_objects if isinstance(obj, OrganizationMember)]
    assert len(members) == 1, "Deve criar exatamente 1 OrganizationMember"
    member = members[0]
    assert member.role == OrgRole.OWNER
    assert member.is_active is True
    assert member.id is not None, "OrganizationMember.id não deve ser None"
    assert member.organization_id == org.id
    assert member.user_id == user.id
    
    # Verifica AuditLogs (3: User, Organization, OrganizationMember)
    audit_logs = [obj for obj in db.added_objects if isinstance(obj, AuditLog)]
    assert len(audit_logs) == 3, f"Deve criar exatamente 3 AuditLogs, got {len(audit_logs)}"
    
    # Verifica entity_id válido (não None) em todos
    for log in audit_logs:
        assert log.entity_id is not None, f"AuditLog entity_id não deve ser None: {log.entity_name}"
        assert isinstance(log.entity_id, uuid.UUID), f"entity_id deve ser UUID: {log.entity_name}"
    
    # Verifica ações corretas
    actions = {log.action for log in audit_logs}
    assert AuditAction.CREATE in actions
    
    entities = {log.entity_name for log in audit_logs}
    assert "User" in entities
    assert "Organization" in entities
    assert "OrganizationMember" in entities
    
    print("✓ user.created: cria User, Organization(pessoal), Settings, Member(OWNER), ProcessedWebhookEvent e 3 AuditLogs com entity_id UUID válido")
    return True


async def test_idempotency():
    """Testa idempotência: reenviar mesmo event_id retorna ignored_duplicate sem duplicar registros."""
    print("\n--- Teste 3: Idempotência ---")
    
    db = MockAsyncSession()
    event_id = "msg_test_001"
    event_type = "user.created"
    data = {
        "id": "clerk_user_123",
        "email_addresses": [{"id": "email_1", "email_address": "test@example.com", "verification": {}}],
        "phone_numbers": [],
        "first_name": "Test",
        "last_name": "User",
        "unsafe_metadata": {},
        "public_metadata": {},
    }
    
    # Primeira chamada - ProcessedWebhookEvent não existe
    db.set_execute_results([
        create_mock_result(scalar_value=None),  # ProcessedWebhookEvent não existe
        create_mock_result(scalar_value=None),  # User não existe
        create_mock_result(scalar_value=None),  # Organization pessoal não existe
    ])
    
    result1 = await process_clerk_webhook(db, event_id, event_type, data)
    assert result1["status"] == "processed"
    
    # Conta objetos adicionados na primeira chamada
    first_call_count = len(db.added_objects)
    
    # Segunda chamada - ProcessedWebhookEvent JÁ EXISTE
    db2 = MockAsyncSession()
    existing_event = ProcessedWebhookEvent(event_id=event_id, provider="clerk")
    db2.set_execute_results([
        create_mock_result(scalar_value=existing_event),  # ProcessedWebhookEvent EXISTE
    ])
    
    result2 = await process_clerk_webhook(db2, event_id, event_type, data)
    
    assert result2["status"] == "ignored_duplicate", f"Status esperado 'ignored_duplicate', got {result2['status']}"
    assert result2["event_id"] == event_id
    assert len(db2.added_objects) == 0, "Não deve adicionar nenhum objeto na segunda chamada"
    
    print("✓ Idempotência: reenvio do mesmo event_id retorna ignored_duplicate sem duplicar registros")
    return True


async def test_user_deleted_anonymization():
    """Testa process_clerk_webhook com user.deleted: anonimização LGPD e AuditLog."""
    print("\n--- Teste 4: user.deleted com Anonimização LGPD ---")
    
    db = MockAsyncSession()
    
    user_id = uuid.uuid4()
    user = create_user(
        id=user_id,
        clerk_user_id="clerk_user_123",
        email="test@example.com",
        full_name="Test User",
        phone="+5511999999999",
        is_anonymized=False,
    )
    
    # Mock: User existe
    db.set_execute_results([
        create_mock_result(scalar_value=None),  # ProcessedWebhookEvent não existe
        create_mock_result(scalar_value=user),  # User existe
        create_mock_result(scalars_all=[]),     # Memberships vazias
    ])
    
    event_id = "msg_test_002"
    event_type = "user.deleted"
    # Payload user.deleted: apenas {"id": "...", "deleted": true}
    data = {
        "id": "clerk_user_123",
        "deleted": True,
    }
    
    result = await process_clerk_webhook(db, event_id, event_type, data)
    
    assert result["status"] == "processed"
    
    # Verifica anonimização
    assert user.is_anonymized is True, "is_anonymized deve ser True"
    assert user.deleted_at is not None, "deleted_at deve ser preenchido"
    assert user.email == f"anon_{user_id}@deleted.manutcar.local", f"Email anonimizado incorreto: {user.email}"
    assert user.full_name == "Usuário Anonimizado", f"Nome anonimizado incorreto: {user.full_name}"
    assert user.phone is None, f"Phone deve ser None: {user.phone}"
    
    # Verifica AuditLog de DELETE
    audit_logs = [obj for obj in db.added_objects if isinstance(obj, AuditLog)]
    delete_logs = [log for log in audit_logs if log.action == AuditAction.DELETE and log.entity_name == "User"]
    assert len(delete_logs) == 1, "Deve criar exatamente 1 AuditLog de DELETE para User"
    
    log = delete_logs[0]
    assert log.entity_id == user_id
    assert log.old_values["email"] == "test@example.com"
    assert log.old_values["full_name"] == "Test User"
    assert log.new_values["email"] == f"anon_{user_id}@deleted.manutcar.local"
    assert log.new_values["full_name"] == "Usuário Anonimizado"
    assert log.new_values["phone"] is None
    assert log.new_values["is_anonymized"] is True
    assert log.new_values["deleted_at"] is not None
    
    print("✓ user.deleted: executa anonimização LGPD (is_anonymized=True, deleted_at, email anonimizado, phone=None) e registra AuditLog")
    return True


async def test_verify_clerk_signature():
    """Testa verify_clerk_signature: valida assinatura Svix real, rejeita inválida com 400, aceita válida com 200."""
    print("\n--- Teste 5: verify_clerk_signature / endpoint /webhooks/clerk ---")
    
    from svix import Webhook
    import json
    
    # Gera assinatura válida usando o secret de teste
    from apps.api.app.core.config import settings as _api_settings
    from apps.api.app.core.config import settings as _api_settings
    from apps.api.app.core.config import settings as _api_settings
    from apps.api.app.core.config import settings as _api_settings
    secret = "whsec_dGVzdF9zZWNyZXRfMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0"
    _api_settings.CLERK_WEBHOOK_SECRET = secret
    _api_settings.CLERK_WEBHOOK_SECRET = secret
    _api_settings.CLERK_WEBHOOK_SECRET = secret
    _api_settings.CLERK_WEBHOOK_SECRET = secret
    wh = Webhook(secret)
    
    payload = {
        "type": "user.created",
        "data": {"id": "clerk_user_123", "email_addresses": []},
        "object": "event"
    }
    payload_bytes = json.dumps(payload).encode()
    
    # Gera headers válidos
    from datetime import datetime as _dt, timezone as _tz
    _ts = _dt.now(_tz.utc)
    _sig = wh.sign('msg_test_svix_001', _ts, payload_bytes.decode('utf-8'))
    headers = {'svix-id': 'msg_test_svix_001', 'svix-timestamp': str(int(_ts.timestamp())), 'svix-signature': _sig}
    svix_id = headers["svix-id"]
    svix_timestamp = headers["svix-timestamp"]
    svix_signature = headers["svix-signature"]
    
    # Mock Request com payload e headers válidos
    mock_request = MagicMock()
    mock_request.body = AsyncMock(return_value=payload_bytes)
    mock_request.headers = {
        "svix-id": svix_id,
        "svix-timestamp": svix_timestamp,
        "svix-signature": svix_signature,
    }
    
    # Testa assinatura VÁLIDA
    try:
        verified_payload = await verify_clerk_signature(
            mock_request,
            svix_id=svix_id,
            svix_timestamp=svix_timestamp,
            svix_signature=svix_signature,
        )
        assert verified_payload["type"] == "user.created"
        assert verified_payload["data"]["id"] == "clerk_user_123"
        print("✓ Assinatura VÁLIDA aceita (HTTP 200)")
    except Exception as e:
        assert False, f"Assinatura válida deveria ser aceita, mas falhou: {e}"
    
    # Testa assinatura INVÁLIDA (assinatura corrompida)
    mock_request_invalid = MagicMock()
    mock_request_invalid.body = AsyncMock(return_value=payload_bytes)
    mock_request_invalid.headers = {
        "svix-id": svix_id,
        "svix-timestamp": svix_timestamp,
        "svix-signature": "invalid_signature",
    }
    
    try:
        await verify_clerk_signature(
            mock_request_invalid,
            svix_id=svix_id,
            svix_timestamp=svix_timestamp,
            svix_signature="invalid_signature",
        )
        assert False, "Assinatura inválida deveria levantar HTTPException 400"
    except Exception as e:
        assert hasattr(e, 'status_code'), "Deveria ser HTTPException"
        assert e.status_code == 400, f"Status code deve ser 400, got {e.status_code}"
        assert "Assinatura Svix inválida" in str(e.detail)
        print("✓ Assinatura INVÁLIDA rejeitada com HTTP 400")
    
    # Testa payload NÃO JSON
    mock_request_bad_json = MagicMock()
    mock_request_bad_json.body = AsyncMock(return_value=b"not json")
    mock_request_bad_json.headers = {
        "svix-id": svix_id,
        "svix-timestamp": svix_timestamp,
        "svix-signature": svix_signature,
    }
    
    try:
        await verify_clerk_signature(
            mock_request_bad_json,
            svix_id=svix_id,
            svix_timestamp=svix_timestamp,
            svix_signature=svix_signature,
        )
        assert False, "Payload não-JSON deveria levantar HTTPException 400"
    except Exception as e:
        assert e.status_code == 400
        assert "Payload não é JSON válido" in str(e.detail)
        print("✓ Payload não-JSON rejeitado com HTTP 400")
    
    return True


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Executa todos os testes de auditoria do Bloco 3B."""
    print("=" * 70)
    print("AUDITORIA BLOCO 3B - Iniciando validações determinísticas")
    print("=" * 70)
    
    tests = [
        test_imports_and_router,
        test_user_created_onboarding,
        test_idempotency,
        test_user_deleted_anonymization,
        test_verify_clerk_signature,
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
        print("AUDITORIA_BLOCO3B_APROVADA")
        return 0
    else:
        print("AUDITORIA_BLOCO3B_REPROVADA")
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
