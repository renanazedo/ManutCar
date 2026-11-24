import json
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from svix import Webhook, WebhookVerificationError

from apps.api.app.core.config import settings
from apps.api.app.db.session import get_db
from apps.api.app.services.sync_service import process_clerk_webhook

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def verify_clerk_signature(
    request: Request,
    svix_id: str = Header(..., alias="svix-id"),
    svix_timestamp: str = Header(..., alias="svix-timestamp"),
    svix_signature: str = Header(..., alias="svix-signature"),
) -> dict[str, Any]:
    """
    Dependency que verifica a assinatura Svix e retorna o payload JSON valido.
    Instancia Webhook aqui (nao no import) para nao quebrar quando CLERK_WEBHOOK_SECRET estiver vazio.
    Levanta 400 se assinatura invalida ou payload malformado.
    """
    payload_bytes = await request.body()

    # 1. Verifica a assinatura. O retorno do verify() e descartado:
    #    o contrato do svix varia entre versoes e pode devolver None.
    try:
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
        wh.verify(
            payload_bytes,
            {
                "svix-id": svix_id,
                "svix-timestamp": svix_timestamp,
                "svix-signature": svix_signature,
            },
        )
    except WebhookVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assinatura Svix invalida: {e}",
        )

    # 2. Parse explicito do corpo ja verificado.
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payload nao e JSON valido: {e}",
        )

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload JSON deve ser um objeto",
        )

    return payload


@router.post("/clerk", status_code=status.HTTP_200_OK)
async def clerk_webhook(
    request: Request,
    payload: dict = Depends(verify_clerk_signature),
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe eventos do Clerk (user.created, organization.created, organizationMembership.created).
    Processa de forma idempotente via process_clerk_webhook.
    """
    event_type = payload.get("type")
    data = payload.get("data", {})
    svix_id = request.headers.get("svix-id")

    if not svix_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header svix-id ausente",
        )

    try:
        result = await process_clerk_webhook(db, svix_id, event_type, data)
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        print(f"ERRO Webhook Clerk [{event_type}]: {e}")
        return {"status": "error", "message": str(e)}