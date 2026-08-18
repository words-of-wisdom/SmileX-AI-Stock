import logging
import time
from datetime import datetime
from typing import List, Optional, Tuple

import httpx
from sqlalchemy import select, func, and_, update, Select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exception.errors import NotFoundError, ConflictError, ForbiddenError
from core.i18n import t
from core.security.openapi import encrypt_secret, decrypt_secret
from database.models.sys.ai_model import (
    SysAiModel,
    SysAiModelBinding,
    AiProviderEnum,
    AiFunctionEnum,
    AI_PROVIDER_DEFAULT_BASE_URL,
    BILLING_MODE_PAY_AS_YOU_GO,
)
from modules.admin.schemas.sys.ai_model import (
    SysAiModelCreate,
    SysAiModelUpdate,
    SysAiModelQueryParams,
    SysAiModelBatchUpdateStatus,
    SysAiModelBindingUpsert,
    AiModelTestResult,
    AiModelFetchModelsRequest,
    AiModelFetchModelsResult,
    AiModelTestConnectionRequest,
)

logger = logging.getLogger(__name__)


def _mask_api_key(encrypted: str) -> str:
    """把加密存储的 api_key 解密后脱敏展示，如 sk-****1234"""
    if not encrypted:
        return ""
    try:
        plain = decrypt_secret(encrypted)
    except Exception:
        return "****"
    if len(plain) <= 8:
        return "****"
    prefix = plain[:3]
    suffix = plain[-4:]
    return f"{prefix}****{suffix}"


class AiModelService:
    """AI 模型配置与场景绑定服务"""

    # ==================== 模型管理 ====================

    @staticmethod
    def build_model_query(query_params: SysAiModelQueryParams) -> Select:
        """构建模型分页查询"""
        base_query = select(SysAiModel)
        conditions = []
        if query_params.name:
            conditions.append(SysAiModel.name.contains(query_params.name))
        if query_params.provider is not None:
            conditions.append(SysAiModel.provider == query_params.provider)
        if query_params.billing_mode is not None:
            conditions.append(SysAiModel.billing_mode == query_params.billing_mode)
        if query_params.status is not None:
            conditions.append(SysAiModel.status == query_params.status)
        if query_params.is_default is not None:
            conditions.append(SysAiModel.is_default == query_params.is_default)
        if conditions:
            base_query = base_query.where(and_(*conditions))
        return base_query.order_by(SysAiModel.is_default.desc(), SysAiModel.id.desc())

    @staticmethod
    async def get_model_list(
        db: AsyncSession, query_params: SysAiModelQueryParams
    ) -> Tuple[List[SysAiModel], int]:
        """获取模型列表（分页）"""
        base_query = AiModelService.build_model_query(query_params)
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        query = base_query
        if query_params.page and query_params.page_size:
            offset = (query_params.page - 1) * query_params.page_size
            query = query.offset(offset).limit(query_params.page_size)
        result = await db.execute(query)
        models = result.scalars().all()
        return models, total

    @staticmethod
    async def get_model(db: AsyncSession, model_id: int) -> SysAiModel:
        """获取单个模型"""
        result = await db.execute(select(SysAiModel).where(SysAiModel.id == model_id))
        model = result.scalar_one_or_none()
        if not model:
            raise NotFoundError(msg=t("ai_model.not_found", id=model_id))
        return model

    @staticmethod
    async def create_model(db: AsyncSession, model_in: SysAiModelCreate) -> SysAiModel:
        """创建模型配置"""
        # 名称唯一校验
        result = await db.execute(
            select(SysAiModel).where(SysAiModel.name == model_in.name)
        )
        if result.scalar_one_or_none():
            raise ConflictError(msg=t("ai_model.name_exist"))

        # 设为默认时，先清掉其他默认
        if model_in.is_default:
            await AiModelService._clear_other_defaults(db)

        model = SysAiModel(
            name=model_in.name,
            provider=model_in.provider,
            base_url=model_in.base_url,
            billing_mode=model_in.billing_mode,
            api_key_encrypted=encrypt_secret(model_in.api_key),
            model_name=model_in.model_name,
            temperature=model_in.temperature,
            max_tokens=model_in.max_tokens,
            is_default=model_in.is_default,
            status=model_in.status,
            remark=model_in.remark,
        )
        db.add(model)
        await db.commit()
        await db.refresh(model)
        logger.info("创建 AI 模型成功，ID: %d，名称: %s", model.id, model.name)
        return model

    @staticmethod
    async def update_model(
        db: AsyncSession, model_id: int, model_in: SysAiModelUpdate
    ) -> SysAiModel:
        """更新模型配置"""
        model = await AiModelService.get_model(db, model_id)

        # 名称唯一校验（排除自身）
        if model_in.name and model_in.name != model.name:
            result = await db.execute(
                select(SysAiModel).where(SysAiModel.name == model_in.name)
            )
            if result.scalar_one_or_none():
                raise ConflictError(msg=t("ai_model.name_exist"))

        # 设为默认时，先清掉其他默认
        if model_in.is_default is True and not model.is_default:
            await AiModelService._clear_other_defaults(db, exclude_id=model_id)

        update_data = model_in.model_dump(exclude_unset=True)
        # api_key 为空表示不修改
        api_key_raw = update_data.pop("api_key", None)
        if api_key_raw:
            model.api_key_encrypted = encrypt_secret(api_key_raw)
        for field, value in update_data.items():
            setattr(model, field, value)

        await db.commit()
        await db.refresh(model)
        logger.info("更新 AI 模型成功，ID: %d", model_id)
        return model

    @staticmethod
    async def batch_update_status(
        db: AsyncSession, batch_in: SysAiModelBatchUpdateStatus
    ) -> int:
        """批量更新模型状态"""
        stmt = (
            update(SysAiModel)
            .where(SysAiModel.id.in_(batch_in.model_ids))
            .values(status=batch_in.status)
        )
        result = await db.execute(stmt)
        await db.commit()
        logger.info("批量更新 AI 模型状态，数量: %d", result.rowcount)
        return result.rowcount

    @staticmethod
    async def delete_model(db: AsyncSession, model_id: int) -> bool:
        """删除模型配置（被启用绑定引用或为默认模型时禁止删除）"""
        model = await AiModelService.get_model(db, model_id)

        # 默认模型禁止删除
        if model.is_default:
            raise ForbiddenError(msg=t("ai_model.is_default"))

        # 被启用的绑定引用时禁止删除
        binding_result = await db.execute(
            select(func.count())
            .select_from(SysAiModelBinding)
            .where(
                and_(
                    SysAiModelBinding.model_id == model_id,
                    SysAiModelBinding.status == True,  # noqa: E712
                )
            )
        )
        if (binding_result.scalar() or 0) > 0:
            raise ForbiddenError(msg=t("ai_model.in_use"))

        await db.delete(model)
        await db.commit()
        logger.info("删除 AI 模型成功，ID: %d", model_id)
        return True

    @staticmethod
    async def _clear_other_defaults(db: AsyncSession, exclude_id: int | None = None) -> None:
        """把其他记录的 is_default 置为 False"""
        stmt = update(SysAiModel).where(SysAiModel.is_default == True).values(is_default=False)  # noqa: E712
        if exclude_id is not None:
            stmt = stmt.where(SysAiModel.id != exclude_id)
        await db.execute(stmt)

    # ==================== 场景绑定管理 ====================

    @staticmethod
    async def list_bindings(db: AsyncSession) -> List[SysAiModelBinding]:
        """获取所有场景绑定（不分页）"""
        result = await db.execute(
            select(SysAiModelBinding).order_by(
                SysAiModelBinding.function_code.asc()
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_binding(
        db: AsyncSession, function_code: AiFunctionEnum
    ) -> Optional[SysAiModelBinding]:
        """按场景编码获取绑定"""
        result = await db.execute(
            select(SysAiModelBinding).where(
                SysAiModelBinding.function_code == function_code
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def upsert_binding(
        db: AsyncSession,
        function_code: AiFunctionEnum,
        binding_in: SysAiModelBindingUpsert,
    ) -> SysAiModelBinding:
        """创建或更新场景绑定"""
        # 校验目标模型存在且启用
        result = await db.execute(
            select(SysAiModel).where(SysAiModel.id == binding_in.model_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            raise NotFoundError(msg=t("ai_model.not_found", id=binding_in.model_id))
        if not model.status:
            raise ForbiddenError(msg=t("ai_model.disabled"))

        existing = await AiModelService.get_binding(db, function_code)
        if existing:
            existing.model_id = binding_in.model_id
            existing.status = binding_in.status
            if binding_in.remark is not None:
                existing.remark = binding_in.remark
            binding = existing
        else:
            binding = SysAiModelBinding(
                function_code=function_code,
                model_id=binding_in.model_id,
                status=binding_in.status,
                remark=binding_in.remark,
            )
            db.add(binding)
        await db.commit()
        await db.refresh(binding)
        logger.info("upsert 场景绑定: %s -> 模型 %d", function_code.value, binding_in.model_id)
        return binding

    @staticmethod
    async def delete_binding(
        db: AsyncSession, function_code: AiFunctionEnum
    ) -> bool:
        """删除场景绑定"""
        binding = await AiModelService.get_binding(db, function_code)
        if not binding:
            raise NotFoundError(msg=t("ai_model.binding_not_found"))
        await db.delete(binding)
        await db.commit()
        logger.info("删除场景绑定: %s", function_code.value)
        return True

    # ==================== 连接测试 ====================

    @staticmethod
    async def test_model_connection(db: AsyncSession, model_id: int) -> AiModelTestResult:
        """测试模型连通性：按 provider 分派，发一次 max_tokens=1 的 ping"""
        model = await AiModelService.get_model(db, model_id)
        try:
            api_key = decrypt_secret(model.api_key_encrypted)
        except Exception as e:
            logger.warning("模型 %d 的 API Key 解密失败: %s", model_id, e)
            return AiModelTestResult(
                success=False,
                latency_ms=0,
                message=str(e),
                provider=model.provider,
                model_name=model.model_name,
            )

        start = time.monotonic()
        try:
            success, message = await AiModelService._do_ping(
                model.provider, model.base_url, model.model_name, api_key
            )
            latency = int((time.monotonic() - start) * 1000)
            if success:
                return AiModelTestResult(
                    success=True,
                    latency_ms=latency,
                    message=t("ai_model.test_success", latency=latency),
                    provider=model.provider,
                    model_name=model.model_name,
                )
            return AiModelTestResult(
                success=False,
                latency_ms=latency,
                message=message,
                provider=model.provider,
                model_name=model.model_name,
            )
        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            return AiModelTestResult(
                success=False,
                latency_ms=latency,
                message=str(e),
                provider=model.provider,
                model_name=model.model_name,
            )

    @staticmethod
    async def _do_ping(
        provider: AiProviderEnum, base_url: str, model_name: str, api_key: str
    ) -> Tuple[bool, str]:
        """按 provider 构造请求并执行 ping"""
        messages = [{"role": "user", "content": "ping"}]

        if provider == AiProviderEnum.ANTHROPIC:
            url = f"{base_url.rstrip('/')}/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": 1,
            }
        else:
            # OpenAI 兼容族（OPENAI/DEEPSEEK/QWEN/ZHIPU/MINIMAX/CUSTOM）
            url = f"{base_url.rstrip('/')}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "content-type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": 1,
            }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 200:
            return True, ""
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"

    # ==================== 即时测试连接 ====================

    @staticmethod
    async def test_connection_by_params(
        db: AsyncSession, req: AiModelTestConnectionRequest
    ) -> AiModelTestResult:
        """用表单当前值即时测试连通性（不落库）：api_key 优先，留空且给 model_id 时用已保存的 key"""
        api_key = (req.api_key or "").strip()
        if not api_key:
            if req.model_id is None:
                return AiModelTestResult(
                    success=False, latency_ms=0,
                    message="缺少 API Key（新填或留空使用已保存）",
                    provider=req.provider, model_name=req.model_name,
                )
            model = await AiModelService.get_model(db, req.model_id)
            try:
                api_key = decrypt_secret(model.api_key_encrypted)
            except Exception as e:
                return AiModelTestResult(
                    success=False, latency_ms=0, message=str(e),
                    provider=req.provider, model_name=req.model_name,
                )

        base_url = (req.base_url or "").strip() or AiModelService.get_default_base_url(
            req.provider, req.billing_mode
        )
        if not base_url:
            return AiModelTestResult(
                success=False, latency_ms=0, message="缺少 API 基础地址",
                provider=req.provider, model_name=req.model_name,
            )

        start = time.monotonic()
        try:
            success, message = await AiModelService._do_ping(
                req.provider, base_url, req.model_name, api_key
            )
            latency = int((time.monotonic() - start) * 1000)
            if success:
                return AiModelTestResult(
                    success=True, latency_ms=latency,
                    message=t("ai_model.test_success", latency=latency),
                    provider=req.provider, model_name=req.model_name,
                )
            return AiModelTestResult(
                success=False, latency_ms=latency, message=message,
                provider=req.provider, model_name=req.model_name,
            )
        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            return AiModelTestResult(
                success=False, latency_ms=latency, message=str(e),
                provider=req.provider, model_name=req.model_name,
            )

    # ==================== 获取模型列表 ====================

    @staticmethod
    async def fetch_provider_models(req: AiModelFetchModelsRequest) -> AiModelFetchModelsResult:
        """拉取供应商可用模型列表（OpenAI 兼容 GET /models 或 Anthropic GET /v1/models）"""
        base_url = (req.base_url or "").strip() or AiModelService.get_default_base_url(
            req.provider, req.billing_mode
        )
        if not base_url:
            return AiModelFetchModelsResult(
                success=False, models=[], message="缺少 API 基础地址"
            )

        if req.provider == AiProviderEnum.ANTHROPIC:
            url = f"{base_url.rstrip('/')}/v1/models"
            headers = {"x-api-key": req.api_key, "anthropic-version": "2023-06-01"}
        else:
            url = f"{base_url.rstrip('/')}/models"
            headers = {"Authorization": f"Bearer {req.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
        except Exception as e:
            return AiModelFetchModelsResult(
                success=False, models=[], message=f"请求失败: {e}"
            )

        if resp.status_code != 200:
            return AiModelFetchModelsResult(
                success=False, models=[],
                message=f"HTTP {resp.status_code}: {resp.text[:200]}",
            )

        # OpenAI 与 Anthropic 的 models 接口均为 {data: [{id: ...}, ...]}
        try:
            data = resp.json().get("data") or []
            models = sorted({
                str(it.get("id")) for it in data if isinstance(it, dict) and it.get("id")
            })
        except Exception as e:
            return AiModelFetchModelsResult(
                success=False, models=[], message=f"响应解析失败: {e}"
            )
        return AiModelFetchModelsResult(success=True, models=models)

    # ==================== 工具方法 ====================

    @staticmethod
    def get_default_base_url(
        provider: AiProviderEnum, billing_mode: str = BILLING_MODE_PAY_AS_YOU_GO
    ) -> str:
        """获取厂商默认 base_url（按 提供商 + 计费模式）"""
        return AI_PROVIDER_DEFAULT_BASE_URL.get((provider, billing_mode), "")
