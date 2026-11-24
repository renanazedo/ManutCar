from fastapi import APIRouter

from app.api.v1.endpoints import webhooks

api_router = APIRouter()

# webhooks.router já define prefix="/webhooks", não repetir aqui
api_router.include_router(webhooks.router)

@api_router.get("/ping", tags=["Health"])
async def ping():
    return {"ping": "pong"}
