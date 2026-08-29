from fastapi import APIRouter

from .endpoints import macro_router

router = APIRouter(prefix="/admin/macro")

router.include_router(macro_router)

__all__ = ["router"]
