"""AI 模型配置表：存储 AI 模型配置（多厂商、API Key 加密存储）与场景→模型绑定关系。"""

import enum

from sqlalchemy import String, Boolean, Integer, Float, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped

from database.models.base import Base


class AiProviderEnum(enum.Enum):
    """AI 模型提供商枚举"""

    OPENAI = "openai"  # OpenAI
    ANTHROPIC = "anthropic"  # Anthropic Claude
    DEEPSEEK = "deepseek"  # DeepSeek
    QWEN = "qwen"  # 通义千问
    ZHIPU = "zhipu"  # 智谱
    CUSTOM = "custom"  # 自定义 OpenAI 兼容


# 各厂商默认 base_url（CUSTOM 由用户填写）
AI_PROVIDER_DEFAULT_BASE_URL = {
    AiProviderEnum.OPENAI: "https://api.openai.com/v1",
    AiProviderEnum.ANTHROPIC: "https://api.anthropic.com",
    AiProviderEnum.DEEPSEEK: "https://api.deepseek.com/v1",
    AiProviderEnum.QWEN: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    AiProviderEnum.ZHIPU: "https://open.bigmodel.cn/api/paas/v4",
    AiProviderEnum.CUSTOM: "",
}


class AiFunctionEnum(enum.Enum):
    """AI 功能场景枚举（功能→模型绑定的场景唯一真源）"""

    STOCK_PICKING = "stock_picking"  # 智能选股
    SENTIMENT_ANALYSIS = "sentiment_analysis"  # 舆情分析
    NEWS_SUMMARY = "news_summary"  # 新闻摘要
    CHAT_QA = "chat_qa"  # 对话问答
    TREND_PREDICTION = "trend_prediction"  # 趋势预测


class SysAiModel(Base):
    """AI 模型配置表 — 存储多厂商 AI 模型配置，API Key 以 Fernet 加密存储。"""

    __table_args__ = (
        UniqueConstraint("name", name="uk_sys_ai_model_name"),
        {"comment": "AI 模型配置表"},
    )

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="模型配置名称"
    )
    provider: Mapped[AiProviderEnum] = mapped_column(
        Enum(AiProviderEnum), nullable=False, comment="AI 模型提供商"
    )
    base_url: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="API 基础地址"
    )
    api_key_encrypted: Mapped[str] = mapped_column(
        String(1000), nullable=False, comment="API Key（Fernet 加密）"
    )
    model_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="模型标识"
    )
    temperature: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=None, comment="温度参数"
    )
    max_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None, comment="最大 token 数"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否为默认模型"
    )
    status: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="状态：True-启用，False-禁用"
    )
    remark: Mapped[str | None] = mapped_column(
        String(500), nullable=True, default=None, comment="备注"
    )


class SysAiModelBinding(Base):
    """AI 场景模型绑定表 — 把固定枚举的业务场景绑定到指定的 AI 模型。"""

    __table_args__ = (
        UniqueConstraint("function_code", name="uk_sys_ai_model_binding_function"),
        {"comment": "AI 场景模型绑定表"},
    )

    function_code: Mapped[AiFunctionEnum] = mapped_column(
        Enum(AiFunctionEnum), nullable=False, index=True, comment="功能场景编码"
    )
    model_id: Mapped[int] = mapped_column(
        ForeignKey("sys_ai_model.id", ondelete="RESTRICT"),
        nullable=False,
        comment="绑定的 AI 模型 ID",
    )
    status: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="状态：True-启用，False-禁用"
    )
    remark: Mapped[str | None] = mapped_column(
        String(500), nullable=True, default=None, comment="备注"
    )
