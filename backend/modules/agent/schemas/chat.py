"""Agent 对话请求/响应 Schema。"""

from typing import Any, Literal, Optional

from pydantic import Field

from modules.common.schemas.base import BaseReqEntity
from database.models.sys.ai_model import AiFunctionEnum


class ToolCallInfo(BaseReqEntity):
    """LLM 发起的工具调用信息（用于前端展示）。"""

    id: str = Field(..., description="工具调用唯一标识")
    name: str = Field(..., description="工具名称")
    arguments: dict[str, Any] = Field(default_factory=dict, description="工具参数")


class ChatMessage(BaseReqEntity):
    """对话消息（OpenAI 格式兼容）。"""

    role: Literal["system", "user", "assistant", "tool"] = Field(
        ..., description="消息角色"
    )
    content: Optional[str] = Field(None, description="消息内容")
    tool_calls: Optional[list[ToolCallInfo]] = Field(
        None, description="assistant 发起的工具调用列表"
    )
    tool_call_id: Optional[str] = Field(
        None, description="tool 角色消息对应的工具调用 ID"
    )
    name: Optional[str] = Field(None, description="tool 角色消息对应的工具名称")


class AgentChatRequest(BaseReqEntity):
    """Agent 对话请求。"""

    function_code: AiFunctionEnum = Field(
        default=AiFunctionEnum.CHAT_QA, description="功能场景编码（决定使用哪个模型）"
    )
    messages: list[ChatMessage] = Field(..., description="对话消息列表")
    stream: bool = Field(True, description="是否流式响应")
