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
    MINIMAX = "minimax"  # MiniMax
    CUSTOM = "custom"  # 自定义 OpenAI 兼容


# 计费模式常量（同一供应商不同计费模式可能对应不同端点）
BILLING_MODE_PAY_AS_YOU_GO = "pay_as_you_go"  # 按量计费
BILLING_MODE_CODING_PLAN = "coding_plan"  # Coding Plan 订阅

BILLING_MODES = (BILLING_MODE_PAY_AS_YOU_GO, BILLING_MODE_CODING_PLAN)

BILLING_MODE_NAMES = {
    BILLING_MODE_PAY_AS_YOU_GO: "按量计费",
    BILLING_MODE_CODING_PLAN: "Coding Plan",
}

# 各厂商默认 base_url，按 (提供商, 计费模式) 二级取值（CUSTOM 由用户填写）。
# 同一供应商两种计费模式端点可能不同：如智谱按量 /api/paas/v4、
# Coding Plan /api/coding/paas/v4（填错会误扣账户余额）；MiniMax 两种模式同域名。
AI_PROVIDER_DEFAULT_BASE_URL = {
    (AiProviderEnum.OPENAI, BILLING_MODE_PAY_AS_YOU_GO): "https://api.openai.com/v1",
    (AiProviderEnum.OPENAI, BILLING_MODE_CODING_PLAN): "https://api.openai.com/v1",
    (AiProviderEnum.ANTHROPIC, BILLING_MODE_PAY_AS_YOU_GO): "https://api.anthropic.com",
    (AiProviderEnum.ANTHROPIC, BILLING_MODE_CODING_PLAN): "https://api.anthropic.com",
    (AiProviderEnum.DEEPSEEK, BILLING_MODE_PAY_AS_YOU_GO): "https://api.deepseek.com/v1",
    (AiProviderEnum.DEEPSEEK, BILLING_MODE_CODING_PLAN): "https://api.deepseek.com/v1",
    (AiProviderEnum.QWEN, BILLING_MODE_PAY_AS_YOU_GO): "https://dashscope.aliyuncs.com/compatible-mode/v1",
    (AiProviderEnum.QWEN, BILLING_MODE_CODING_PLAN): "https://dashscope.aliyuncs.com/compatible-mode/v1",
    (AiProviderEnum.ZHIPU, BILLING_MODE_PAY_AS_YOU_GO): "https://open.bigmodel.cn/api/paas/v4",
    (AiProviderEnum.ZHIPU, BILLING_MODE_CODING_PLAN): "https://open.bigmodel.cn/api/coding/paas/v4",
    (AiProviderEnum.MINIMAX, BILLING_MODE_PAY_AS_YOU_GO): "https://api.minimaxi.com/v1",
    (AiProviderEnum.MINIMAX, BILLING_MODE_CODING_PLAN): "https://api.minimaxi.com/v1",
    (AiProviderEnum.CUSTOM, BILLING_MODE_PAY_AS_YOU_GO): "",
    (AiProviderEnum.CUSTOM, BILLING_MODE_CODING_PLAN): "",
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
        # values_callable：按枚举 value（小写）序列化，与迁移 0008 建的 PG enum 成员一致；
        # 默认按 name（大写）序列化会导致参数绑定报 invalid input value for enum
        Enum(AiProviderEnum, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, comment="AI 模型提供商",
    )
    base_url: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="API 基础地址"
    )
    billing_mode: Mapped[str] = mapped_column(
        String(20), nullable=False,
        insert_default=BILLING_MODE_PAY_AS_YOU_GO,
        comment="计费模式：pay_as_you_go-按量计费，coding_plan-Coding Plan 订阅",
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
        # 同 provider：按枚举 value（小写）序列化，与 PG enum 成员一致
        Enum(AiFunctionEnum, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, index=True, comment="功能场景编码",
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
