import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT, os.path.join(ROOT, "apps", "api")):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/manutcar_test")

from httpx import ASGITransport, AsyncClient
from svix import Webhook
from apps.api.app.core.config import settings
from apps.api.app.db.session import get_db
from apps.api.app.main import app
from apps.api.app.services.sync_service import process_clerk_webhook
from manutcar_db.enums import OrgRole
from manutcar_db.models.finance_audit import AuditLog, ProcessedWebhookEvent
from manutcar_db.models.identity import Organization, OrganizationMember, OrganizationSettings, User


class FakeScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)

    def first(self):
        return self._items[0] if self._items else None


class FakeResult:
    def __init__(self, items):
        self._items = items

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None

    def scalars(self):
        return FakeScalars(self._items)


class FakeSession:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, obj):
        if getattr(obj, "id", None) is None and hasattr(obj, "id"):
            try:
                obj.id = uuid.uuid4()
            except Exception:
                pass
        self.added.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass

    async def execute(self, stmt):
        sql = str(stmt)
        params = stmt.compile().params
        vals = list(params.values())
        if "processed_webhook_events" in sql:
            found = [x for x in self.added if isinstance(x, ProcessedWebhookEvent) and x.event_id in vals]
            return FakeResult(found)
        if "FROM users" in sql:
            found = [x for x in self.added if isinstance(x, User) and x.clerk_user_id in vals]
            return FakeResult(found)
        if "FROM organizations" in sql:
            found = [x for x in self.added if isinstance(x, Organization) and x.is_personal_workspace]
            return FakeResult(found)
        if "FROM organization_members" in sql:
            found = [x for x in self.added if isinstance(x, OrganizationMember)]
            return FakeResult(found)
        return FakeResult([])


async def main():
    db = FakeSession()

    # 1. Onboarding automatico em user.created
    res1 = await process_clerk_webhook(
        db,
        "msg_001",
        "user.created",
        {
            "id": "user_clerk_999",
            "first_name": "Renan",
            "last_name": "Oliveira",
            "email_addresses": [{"id": "em_1", "email_address": "renansuporte@gmail.com"}],
            "phone_numbers": [{"id": "ph_1", "phone_number": "+5521999999999"}],
        },
    )
    assert res1["status"] == "processed", res1
    users = [x for x in db.added if isinstance(x, User)]
    orgs = [x for x in db.added if isinstance(x, Organization)]
    settings_list = [x for x in db.added if isinstance(x, OrganizationSettings)]
    members = [x for x in db.added if isinstance(x, OrganizationMember)]
    audits = [x for x in db.added if isinstance(x, AuditLog)]
    assert len(users) == 1 and users[0].clerk_user_id == "user_clerk_999"
    assert len(orgs) == 1 and orgs[0].is_personal_workspace is True
    assert len(settings_list) == 1
    assert len(members) == 1 and members[0].role == OrgRole.OWNER
    assert len(audits) == 3 and all(isinstance(a.entity_id, uuid.UUID) for a in audits)
    print("OK 1: user.created + Onboarding Pessoal + 3 AuditLogs")

    # 2. Idempotencia
    res_dup = await process_clerk_webhook(db, "msg_001", "user.created", {"id": "user_clerk_999"})
    assert res_dup["status"] == "ignored_duplicate", res_dup
    assert len([x for x in db.added if isinstance(x, User)]) == 1
    print("OK 2: Idempotencia garantida")

    # 3. Anonimizacao LGPD em user.deleted
    res_del = await process_clerk_webhook(db, "msg_002", "user.deleted", {"id": "user_clerk_999", "deleted": True})
    assert res_del["status"] == "processed", res_del
    assert users[0].is_anonymized is True
    assert users[0].phone is None
    assert "@deleted.manutcar.local" in users[0].email
    print("OK 3: Anonimizacao LGPD (RN-AUD-03)")

    # 4. Rota HTTP /api/v1/webhooks/clerk + Assinatura Svix real
    secret = "whsec_dGVzdF9zZWNyZXRfMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0"
    settings.CLERK_WEBHOOK_SECRET = secret

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    payload_bytes = json.dumps({"type": "ping.test", "data": {}}).encode("utf-8")
    ts = datetime.now(timezone.utc)
    wh = Webhook(secret)
    sig = wh.sign("msg_http_001", ts, payload_bytes.decode("utf-8"))
    valid_headers = {
        "svix-id": "msg_http_001",
        "svix-timestamp": str(int(ts.timestamp())),
        "svix-signature": sig,
        "content-type": "application/json",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r_bad = await client.post("/api/v1/webhooks/clerk", content=payload_bytes, headers={**valid_headers, "svix-signature": "v1,invalida"})
        assert r_bad.status_code == 400, f"Esperado 400, veio {r_bad.status_code}"

        r_ok = await client.post("/api/v1/webhooks/clerk", content=payload_bytes, headers=valid_headers)
        assert r_ok.status_code == 200, f"Esperado 200, veio {r_ok.status_code}: {r_ok.text}"
        assert r_ok.json()["status"] == "processed"

    print("OK 4: Rota /api/v1/webhooks/clerk + Svix HTTP 400/200")
    print("AUDITORIA_BLOCO3B_APROVADA")


if __name__ == "__main__":
    asyncio.run(main())

