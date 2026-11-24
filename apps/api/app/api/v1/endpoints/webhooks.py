import json
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from svix import Webhook, WebhookVerificationError

from app.core.config import settings
from packages.db.src.manutcar.db.session import get_db_session

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Instância do Webhook Svix (verificação de assinatura)
# CLERK_WEBHOOK_SECRET vem do .env (whsec_...)
wh = Webhook(settings.CLERK_WEBHOOK_SECRET)


async def verify_clerk_signature(
    request: Request,
    svix_id: str = Header(..., alias="svix-id"),
    svix_timestamp: str = Header(..., alias="svix-timestamp"),
    svix_signature: str = Header(..., alias="svix-signature"),
) -> dict[str, Any]:
    """
    Dependency que verifica a assinatura Svix e retorna o payload JSON válido.
    Levanta 400 se assinatura inválida ou payload malformado.
    """
    payload_bytes = await request.body()
    try:
        # Svix espera headers como dicionário
        headers = {
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature,
        }
        # verify retorna o payload dict se válido
        verified_payload = wh.verify(payload_bytes, headers)
        return verified_payload
    except WebhookVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assinatura Svix inválida: {e}",
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload não é JSON válido",
        )


@router.post("/clerk", status_code=status.HTTP_200_OK)
async def clerk_webhook(
    payload: dict = Depends(verify_clerk_signature),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Recebe eventos do Clerk (user.created, organization.created, organizationMembership.created).
    Processa de forma idempotente (upsert) para sincronizar tabelas locais.
    """
    event_type = payload.get("type")
    data = payload.get("data", {})

    # Import local para evitar circular dependency no topo do arquivo
    from app.services.sync_service import sync_clerk_event

    try:
        await sync_clerk_event(db, event_type, data)
        await db.commit()
    except Exception as e:
        await db.rollback()
        # Log estruturado seria ideal aqui (structlog)
        print(f"ERRO Webhook Clerk [{event_type}]: {e}")
        # Retornamos 200 mesmo em erro de negócio para não travar retry do Clerk
        # mas idealmente teríamos uma Dead Letter Queue (Inc 2)
        return {"status": "error", "message": str(e)}

    return {"status": "success", "event": event_type}
