import logging
from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.decorators.operation_log import log_operation
from core.i18n import t
from core.response.response_schema import ResponseModel, ResponsePageModel, response_base
from database.db_manager import get_session
from database.models.sys.ai_model import AiFunctionEnum
from database.models.sys.user import SysUser
from modules.admin.deps.auth.permission import require_permission
from modules.admin.deps.auth.user_manager import current_user
from modules.admin.schemas.sys.ai_model import (
    SysAiModelCreate,
    SysAiModelUpdate,
    SysAiModelQueryParams,
    SysAiModelResponseData,
    SysAiModelSimpleResponse,
    SysAiModelBatchUpdateStatus,
    SysAiModelBindingUpsert,
    SysAiModelBindingResponseData,
    AiModelTestResult,
)
from modules.admin.services.sys import AiModelService
from modules.common.schemas.page import PageRequest, get_page_params, get_paginated_results

logger = logging.getLogger(__name__)

ai_model_router = APIRouter(
    prefix="/ai-model", tags=["AI模型配置"], dependencies=[Depends(current_user)]
)


# ==================== 模型管理 ====================


@ai_model_router.get(
    "/list",
    response_model=ResponsePageModel[SysAiModelResponseData],
    dependencies=[Depends(require_permission("sys:ai_model:list"))],
)
async def get_ai_model_list(
    query_params: SysAiModelQueryParams = Depends(),
    page_params: PageRequest = Depends(get_page_params),
    db: AsyncSession = Depends(get_session),
):
    """获取 AI 模型列表（分页）"""
    query = AiModelService.build_model_query(query_params)
    page_data = await get_paginated_results(
        db=db,
        page_params=page_params,
        query=query,
        schema=SysAiModelResponseData,
    )
    return response_base.page(data=page_data)


@ai_model_router.get(
    "/all", response_model=ResponseModel[List[SysAiModelSimpleResponse]]
)
async def get_all_ai_models(
    db: AsyncSession = Depends(get_session),
):
    """获取所有启用的 AI 模型（下拉选择用，不分页）"""
    from sqlalchemy import select
    from database.models.sys.ai_model import SysAiModel
    result = await db.execute(
        select(SysAiModel)
        .where(SysAiModel.status == True)  # noqa: E712
        .order_by(SysAiModel.is_default.desc(), SysAiModel.id.desc())
    )
    models = result.scalars().all()
    records = [SysAiModelSimpleResponse.model_validate(m) for m in models]
    return response_base.success(data=records)


@ai_model_router.get(
    "/{model_id}", response_model=ResponseModel[SysAiModelResponseData]
)
async def get_ai_model(
    model_id: int,
    db: AsyncSession = Depends(get_session),
):
    """获取单个 AI 模型"""
    model = await AiModelService.get_model(db, model_id)
    response_data = SysAiModelResponseData.model_validate(model)
    return response_base.success(data=response_data)


@ai_model_router.post(
    "/add",
    response_model=ResponseModel[SysAiModelResponseData],
    dependencies=[Depends(require_permission("sys:ai_model:add"))],
)
@log_operation(module="ai_model", action="create", description="创建AI模型配置")
async def create_ai_model(
    request: Request,
    model_in: SysAiModelCreate,
    db: AsyncSession = Depends(get_session),
    user: SysUser = Depends(current_user),
):
    """创建 AI 模型配置"""
    model = await AiModelService.create_model(db, model_in)
    response_data = SysAiModelResponseData.model_validate(model)
    return response_base.success(data=response_data, msg=t("common.create_success"))


@ai_model_router.put(
    "/{model_id}",
    response_model=ResponseModel[SysAiModelResponseData],
    dependencies=[Depends(require_permission("sys:ai_model:edit"))],
)
@log_operation(module="ai_model", action="update", description="更新AI模型配置")
async def update_ai_model(
    model_id: int,
    request: Request,
    model_in: SysAiModelUpdate,
    db: AsyncSession = Depends(get_session),
    user: SysUser = Depends(current_user),
):
    """更新 AI 模型配置"""
    model = await AiModelService.update_model(db, model_id, model_in)
    response_data = SysAiModelResponseData.model_validate(model)
    return response_base.success(data=response_data, msg=t("common.update_success"))


@ai_model_router.put(
    "/batch/status",
    response_model=ResponseModel,
    dependencies=[Depends(require_permission("sys:ai_model:edit"))],
)
@log_operation(module="ai_model", action="batch_update_status", description="批量更新AI模型状态")
async def batch_update_ai_model_status(
    request: Request,
    batch_in: SysAiModelBatchUpdateStatus,
    db: AsyncSession = Depends(get_session),
    user: SysUser = Depends(current_user),
):
    """批量更新 AI 模型状态"""
    updated_count = await AiModelService.batch_update_status(db, batch_in)
    return response_base.success(msg=t("common.batch_update_count", count=updated_count))


@ai_model_router.delete(
    "/{model_id}",
    response_model=ResponseModel,
    dependencies=[Depends(require_permission("sys:ai_model:delete"))],
)
@log_operation(module="ai_model", action="delete", description="删除AI模型配置")
async def delete_ai_model(
    model_id: int,
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: SysUser = Depends(current_user),
):
    """删除 AI 模型配置"""
    await AiModelService.delete_model(db, model_id)
    return response_base.success(msg=t("common.delete_success"))


# ==================== 场景绑定管理 ====================


@ai_model_router.get(
    "/binding/list",
    response_model=ResponseModel[List[SysAiModelBindingResponseData]],
)
async def get_ai_model_binding_list(
    db: AsyncSession = Depends(get_session),
):
    """获取所有场景绑定列表（不分页）"""
    bindings = await AiModelService.list_bindings(db)
    # 查所有模型做冗余字段填充
    from sqlalchemy import select
    from database.models.sys.ai_model import SysAiModel
    model_result = await db.execute(select(SysAiModel))
    model_map = {m.id: m for m in model_result.scalars().all()}

    records: List[SysAiModelBindingResponseData] = []
    for b in bindings:
        m = model_map.get(b.model_id)
        resp = SysAiModelBindingResponseData(
            id=b.id,
            function_code=b.function_code,
            model_id=b.model_id,
            status=b.status,
            remark=b.remark,
            model_name=m.name if m else None,
            provider=m.provider if m else None,
            created_at=b.created_at,
            updated_at=b.updated_at,
        )
        records.append(resp)
    return response_base.success(data=records)


@ai_model_router.put(
    "/binding/{function_code}",
    response_model=ResponseModel[SysAiModelBindingResponseData],
    dependencies=[Depends(require_permission("sys:ai_model:edit"))],
)
@log_operation(module="ai_model", action="upsert_binding", description="设置场景模型绑定")
async def upsert_ai_model_binding(
    function_code: AiFunctionEnum,
    request: Request,
    binding_in: SysAiModelBindingUpsert,
    db: AsyncSession = Depends(get_session),
    user: SysUser = Depends(current_user),
):
    """创建或更新场景→模型绑定"""
    binding = await AiModelService.upsert_binding(db, function_code, binding_in)
    response_data = SysAiModelBindingResponseData.model_validate(binding)
    return response_base.success(data=response_data, msg=t("common.save_success"))


@ai_model_router.delete(
    "/binding/{function_code}",
    response_model=ResponseModel,
    dependencies=[Depends(require_permission("sys:ai_model:delete"))],
)
@log_operation(module="ai_model", action="delete_binding", description="删除场景模型绑定")
async def delete_ai_model_binding(
    function_code: AiFunctionEnum,
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: SysUser = Depends(current_user),
):
    """删除场景绑定"""
    await AiModelService.delete_binding(db, function_code)
    return response_base.success(msg=t("common.delete_success"))


# ==================== 连接测试 ====================


@ai_model_router.post(
    "/{model_id}/test",
    response_model=ResponseModel[AiModelTestResult],
    dependencies=[Depends(require_permission("sys:ai_model:list"))],
)
async def test_ai_model(
    model_id: int,
    db: AsyncSession = Depends(get_session),
):
    """测试 AI 模型连通性"""
    result = await AiModelService.test_model_connection(db, model_id)
    return response_base.success(data=result)
