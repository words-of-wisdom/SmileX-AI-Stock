from fastapi import APIRouter

from .endpoints import chat_router

router = APIRouter(prefix="/admin/agent")

router.include_router(chat_router)

__all__ = ["router"]
