from fastapi import APIRouter

from app.api.v1.endpoints import webhooks

api_router = APIRouter()

api_router.include_router(webhooks.router, prefix="/webhooks")

@api_router.get("/ping", tags=["Health"])
async def ping():
    return {"ping": "pong"}
