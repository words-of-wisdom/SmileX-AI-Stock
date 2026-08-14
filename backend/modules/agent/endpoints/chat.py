"""Agent 对话端点 —— SSE 流式响应。"""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_manager import get_session
from database.models.sys.user import SysUser
from modules.admin.deps.auth.user_manager import current_user
from modules.agent.schemas.chat import AgentChatRequest
from modules.agent.services.agent_service import AgentService

logger = logging.getLogger(__name__)

chat_router = APIRouter(prefix="/chat", tags=["AI Agent"])


@chat_router.post(
    "",
    summary="Agent 对话（SSE 流式）",
    dependencies=[Depends(current_user)],
)
async def agent_chat(
    chat_in: AgentChatRequest,
    db: AsyncSession = Depends(get_session),
    user: SysUser = Depends(current_user),
):
    """Agent 对话接口，返回 SSE 流式响应。

    事件流格式（每行 data: JSON）：
    - {"type": "token", "content": "..."}       LLM 文字增量
    - {"type": "tool_call", ...}                 正在调用工具
    - {"type": "tool_result", ...}               工具执行结果
    - {"type": "done"}                           结束
    - {"type": "error", "message": "..."}        错误

    注意：SSE 响应不走统一 { code, msg, data } 包装，
    错误信息通过 error 事件传递。
    """
    messages = [m.model_dump(exclude_none=True) for m in chat_in.messages]

    async def event_stream():
        async for event in AgentService.run_agent_stream(
            db, messages, chat_in.function_code
        ):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
            "Connection": "keep-alive",
        },
    )
