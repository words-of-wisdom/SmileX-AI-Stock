from fastapi import APIRouter

from .endpoints import analysis_router

router = APIRouter(prefix="/admin/analysis")

router.include_router(analysis_router)

__all__ = ["router"]
