from datetime import datetime
from typing import Annotated, Optional, List

from pydantic import Field, ConfigDict, field_serializer, field_validator, model_validator, BeforeValidator

from modules.common.schemas.base import BaseRespEntity, BaseReqEntity, BoolField
from modules.common.schemas.page import PageRequest
from database.models.sys.ai_model import (
    AiProviderEnum,
    AiFunctionEnum,
    BILLING_MODES,
)


def _mask_api_key_value(encrypted: str) -> str:
    """把加密存储的 api_key 解密后脱敏展示，如 sk-****1234"""
    if not encrypted:
        return ""
    try:
        from core.security.openapi import decrypt_secret
        plain = decrypt_secret(encrypted)
    except Exception:
        return "****"
    if len(plain) <= 8:
        return "****"
    return f"{plain[:3]}****{plain[-4:]}"


def _parse_provider(v):
    """解析 provider 参数，支持字符串转 AiProviderEnum"""
    if v is None or v == "":
        return None
    if isinstance(v, AiProviderEnum):
        return v
    if isinstance(v, str):
        stripped = v.strip()
        if not stripped:
            return None
        try:
            return AiProviderEnum(stripped)
        except ValueError:
            return None
    return None


def _parse_function(v):
    """解析 function_code 参数，支持字符串转 AiFunctionEnum"""
    if v is None or v == "":
        return None
    if isinstance(v, AiFunctionEnum):
        return v
    if isinstance(v, str):
        stripped = v.strip()
        if not stripped:
            return None
        try:
            return AiFunctionEnum(stripped)
        except ValueError:
            return None
    return None


def _parse_billing_mode(v):
    """解析 billing_mode 参数（写入/请求体用），非法值回退按量计费"""
    if v in BILLING_MODES:
        return v
    return BILLING_MODES[0]


def _parse_billing_mode_query(v):
    """查询参数用：空串/None/非法值均视为不过滤（返回 None），
    避免未选筛选条件时被强制按 pay_as_you_go 过滤导致 Coding Plan 记录消失"""
    if v in BILLING_MODES:
        return v
    return None


# ==================== AI 模型 Schema ====================


class SysAiModelQueryParams(PageRequest):
    """AI 模型查询参数"""

    name: Optional[str] = Field(None, description="模型配置名称，支持模糊查询")
    # 查询参数必须是字段级 Annotated 校验器：FastAPI 会把 query model 拆成逐字段校验，
    # 类级 field_validator(mode="before") 在该路径不生效，空串会直接触发 Enum 422
    provider: Annotated[
        Optional[AiProviderEnum], BeforeValidator(_parse_provider)
    ] = Field(None, description="提供商类型")
    billing_mode: Annotated[
        Optional[str], BeforeValidator(_parse_billing_mode_query)
    ] = Field(None, description="计费模式过滤：pay_as_you_go/coding_plan")
    status: BoolField = Field(None, description="状态：True-启用，False-禁用")
    is_default: BoolField = Field(None, description="是否为默认模型")


class SysAiModelCreate(BaseReqEntity):
    """AI 模型创建请求"""

    name: str = Field(..., description="模型配置名称", min_length=1, max_length=100)
    provider: AiProviderEnum = Field(..., description="AI 模型提供商")
    base_url: str = Field(..., description="API 基础地址", min_length=1, max_length=500)
    billing_mode: Annotated[
        str, BeforeValidator(_parse_billing_mode)
    ] = Field(BILLING_MODES[0], description="计费模式：pay_as_you_go/coding_plan")
    api_key: str = Field(..., description="API Key（明文，后端加密存储）", min_length=1, max_length=500)
    model_name: str = Field(..., description="模型标识", min_length=1, max_length=200)
    temperature: Optional[float] = Field(None, description="温度参数", ge=0, le=2)
    max_tokens: Optional[int] = Field(None, description="最大 token 数", ge=1)
    is_default: bool = Field(False, description="是否为默认模型")
    status: bool = Field(True, description="状态：True-启用，False-禁用")
    remark: Optional[str] = Field(None, description="备注", max_length=500)


class SysAiModelUpdate(BaseReqEntity):
    """AI 模型更新请求"""

    name: Optional[str] = Field(None, description="模型配置名称", max_length=100)
    provider: Optional[AiProviderEnum] = Field(None, description="AI 模型提供商")
    base_url: Optional[str] = Field(None, description="API 基础地址", max_length=500)
    billing_mode: Annotated[
        Optional[str], BeforeValidator(_parse_billing_mode)
    ] = Field(None, description="计费模式：pay_as_you_go/coding_plan")
    api_key: Optional[str] = Field(
        None, description="API Key（留空表示不修改，非空则重新加密）", max_length=500
    )
    model_name: Optional[str] = Field(None, description="模型标识", max_length=200)
    temperature: Optional[float] = Field(None, description="温度参数", ge=0, le=2)
    max_tokens: Optional[int] = Field(None, description="最大 token 数", ge=1)
    is_default: BoolField = Field(None, description="是否为默认模型")
    status: BoolField = Field(None, description="状态：True-启用，False-禁用")
    remark: Optional[str] = Field(None, description="备注", max_length=500)


class SysAiModelResponseData(BaseRespEntity):
    """AI 模型详细响应（不含明文 API Key，仅返回脱敏值）"""

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _orm_to_masked_dict(cls, data):
        """ORM 对象输入时，把加密 key 转为脱敏值注入到 schema 字段"""
        if hasattr(data, "api_key_encrypted"):
            encrypted = getattr(data, "api_key_encrypted", "")
            data = {
                "id": data.id,
                "name": data.name,
                "provider": data.provider,
                "base_url": data.base_url,
                "billing_mode": data.billing_mode,
                "model_name": data.model_name,
                "temperature": data.temperature,
                "max_tokens": data.max_tokens,
                "is_default": data.is_default,
                "status": data.status,
                "remark": data.remark,
                "api_key_masked": _mask_api_key_value(encrypted),
                "created_at": data.created_at,
                "updated_at": data.updated_at,
            }
        return data

    id: int = Field(..., description="模型ID")
    name: str = Field(..., description="模型配置名称")
    provider: AiProviderEnum = Field(..., description="AI 模型提供商")
    base_url: str = Field(..., description="API 基础地址")
    billing_mode: str = Field(BILLING_MODES[0], description="计费模式：pay_as_you_go/coding_plan")
    model_name: str = Field(..., description="模型标识")
    temperature: Optional[float] = Field(None, description="温度参数")
    max_tokens: Optional[int] = Field(None, description="最大 token 数")
    is_default: bool = Field(..., description="是否为默认模型")
    status: bool = Field(..., description="状态")
    remark: Optional[str] = Field(None, description="备注")
    api_key_masked: Optional[str] = Field(None, description="API Key 脱敏值")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    @field_serializer("is_default")
    def serialize_is_default_output(self, value: bool):
        if isinstance(value, bool):
            return "1" if value else "2"
        return value


class SysAiModelSimpleResponse(BaseRespEntity):
    """AI 模型简单响应（下拉选择用）"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="模型ID")
    name: str = Field(..., description="模型配置名称")
    model_name: str = Field(..., description="模型标识")
    provider: AiProviderEnum = Field(..., description="AI 模型提供商")
    is_default: bool = Field(..., description="是否为默认模型")

    @field_serializer("is_default")
    def serialize_is_default_output(self, value: bool):
        if isinstance(value, bool):
            return "1" if value else "2"
        return value


class SysAiModelBatchUpdateStatus(BaseReqEntity):
    """AI 模型批量更新状态请求"""

    model_ids: List[int] = Field(..., description="模型ID列表")
    status: bool = Field(..., description="要设置的状态：True-启用，False-禁用")


# ==================== 场景绑定 Schema ====================


class SysAiModelBindingQueryParams(BaseReqEntity):
    """场景绑定查询参数"""

    function_code: Optional[AiFunctionEnum] = Field(None, description="功能场景编码")
    status: BoolField = Field(None, description="状态")

    @field_validator("function_code", mode="before")
    @classmethod
    def parse_function_field(cls, v):
        return _parse_function(v)


class SysAiModelBindingUpsert(BaseReqEntity):
    """场景绑定 upsert 请求"""

    model_id: int = Field(..., description="绑定的 AI 模型 ID")
    status: bool = Field(True, description="状态：True-启用，False-禁用")
    remark: Optional[str] = Field(None, description="备注", max_length=500)


class SysAiModelBindingResponseData(BaseRespEntity):
    """场景绑定详细响应"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="绑定ID")
    function_code: AiFunctionEnum = Field(..., description="功能场景编码")
    model_id: int = Field(..., description="绑定的 AI 模型 ID")
    status: bool = Field(..., description="状态")
    remark: Optional[str] = Field(None, description="备注")
    model_name: Optional[str] = Field(None, description="绑定模型配置名称（冗余展示）")
    provider: Optional[AiProviderEnum] = Field(None, description="绑定模型提供商（冗余展示）")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


# ==================== 连接测试 Schema ====================


class AiModelTestResult(BaseReqEntity):
    """模型连接测试结果"""

    success: bool = Field(..., description="是否连接成功")
    latency_ms: int = Field(0, description="延迟（毫秒）")
    message: str = Field("", description="结果消息")
    provider: AiProviderEnum = Field(..., description="提供商类型")
    model_name: str = Field(..., description="测试模型标识")


# ==================== 获取模型列表 Schema ====================


class AiModelFetchModelsRequest(BaseReqEntity):
    """拉取供应商可用模型列表请求（用于模型标识下拉，key 必填）"""

    provider: AiProviderEnum = Field(..., description="AI 模型提供商")
    base_url: Optional[str] = Field(
        None, description="API 基础地址，留空按供应商+计费模式取默认值", max_length=500
    )
    billing_mode: Annotated[
        str, BeforeValidator(_parse_billing_mode)
    ] = Field(BILLING_MODES[0], description="计费模式：pay_as_you_go/coding_plan")
    api_key: str = Field(
        ..., min_length=1, max_length=500,
        description="API Key（明文，仅本次请求使用，不落库）",
    )


class AiModelFetchModelsResult(BaseReqEntity):
    """拉取模型列表结果"""

    success: bool = Field(..., description="是否成功")
    models: List[str] = Field(default_factory=list, description="可用模型标识列表")
    message: str = Field("", description="失败原因")


class AiModelTestConnectionRequest(BaseReqEntity):
    """即时测试连接请求（用表单当前值测试，不落库；api_key 留空且传 model_id 时用已保存的 key）"""

    provider: AiProviderEnum = Field(..., description="AI 模型提供商")
    base_url: Optional[str] = Field(
        None, description="API 基础地址，留空按供应商+计费模式取默认值", max_length=500
    )
    billing_mode: Annotated[
        str, BeforeValidator(_parse_billing_mode)
    ] = Field(BILLING_MODES[0], description="计费模式：pay_as_you_go/coding_plan")
    model_name: str = Field(..., description="模型标识", min_length=1, max_length=200)
    api_key: Optional[str] = Field(
        None, max_length=500,
        description="API Key（明文，留空且提供 model_id 时使用已保存的 key）",
    )
    model_id: Optional[int] = Field(
        None, description="已有模型 ID（api_key 留空时用于取已保存的 key）"
    )
