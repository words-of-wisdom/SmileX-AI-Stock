from fastapi import APIRouter

from .endpoints import research_router

router = APIRouter(prefix="/admin/research")

router.include_router(research_router)

__all__ = ["router"]
