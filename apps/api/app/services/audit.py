import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from manutcar_db.models.finance_audit import AuditLog
from manutcar_db.enums import AuditAction


async def record_audit_log(
    db: AsyncSession,
    *,
    organization_id: Optional[uuid.UUID],
    actor_user_id: Optional[uuid.UUID],
    entity_name: str,
    entity_id: uuid.UUID,
    action: AuditAction,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
) -> AuditLog:
    """
    Insere um registro de auditoria imutável na tabela AuditLog.
    RN-AUD-01: Nunca altera ou apaga registros anteriores.
    Não faz commit - a transação é gerenciada pelo caller.
    """
    log = AuditLog(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        entity_name=entity_name,
        entity_id=entity_id,
        action=action,
        old_values=old_values,
        new_values=new_values,
    )
    db.add(log)
    await db.flush()
    return log
