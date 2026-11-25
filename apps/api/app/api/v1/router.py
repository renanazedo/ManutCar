from fastapi import APIRouter
from apps.api.app.api.v1.endpoints import fleet, operations, webhooks

api_router = APIRouter()
api_router.include_router(webhooks.router)
api_router.include_router(fleet.router)
api_router.include_router(operations.router)


@api_router.get("/ping", tags=["Health"])
async def ping():
    return {"ping": "pong"}
