from fastapi import APIRouter

from .endpoints import financial_router

router = APIRouter(prefix="/admin/financial")

router.include_router(financial_router)

__all__ = ["router"]
