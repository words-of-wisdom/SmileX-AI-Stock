"""
统一 LLM 调用客户端 —— 封装多厂商流式对话与工具调用。

设计要点：
- 复用 sys_ai_model 表的配置（凭据加密存储、场景绑定、默认回退）
- 按 provider 分派请求格式：OpenAI 族走 /chat/completions，Anthropic 走 /v1/messages
- 流式输出统一 yield 为 OpenAI 风格的中间结构（StreamChunk），由 agent_service 转为 SSE
- 工具调用统一使用 OpenAI Function Calling 格式，Anthropic 的差异在本层透明转换
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exception.errors import CustomError
from core.response.response_code import CustomErrorCode
from core.security.openapi import decrypt_secret
from database.models.sys.ai_model import (
    SysAiModel,
    SysAiModelBinding,
    AiProviderEnum,
    AiFunctionEnum,
)

logger = logging.getLogger(__name__)


# ==================== 数据结构 ====================


@dataclass
class StreamChunk:
    """LLM 流式输出的中间统一结构。"""

    content: str = ""  # 本次 chunk 的文字增量
    tool_calls: list[dict] = field(default_factory=list)  # 累积的工具调用（OpenAI 格式）
    finish_reason: Optional[str] = None  # stop / tool_calls / length


@dataclass
class ResolvedModel:
    """解析后的模型配置（含解密后的 api_key）。"""

    model: SysAiModel
    api_key: str


# ==================== 模型解析 ====================


async def resolve_model(
    db: AsyncSession, function_code: AiFunctionEnum
) -> ResolvedModel:
    """
    解析场景对应的模型：场景绑定优先（且启用），否则回退默认模型。

    与 AiModelService 的规则保持一致。
    """
    # 1. 查场景绑定
    binding_result = await db.execute(
        select(SysAiModelBinding)
        .where(
            SysAiModelBinding.function_code == function_code,
            SysAiModelBinding.status == True,  # noqa: E712
            SysAiModelBinding.deleted_at.is_(None),
        )
        .limit(1)
    )
    binding = binding_result.scalar_one_or_none()

    model: Optional[SysAiModel] = None
    if binding:
        result = await db.execute(
            select(SysAiModel).where(
                SysAiModel.id == binding.model_id,
                SysAiModel.status == True,  # noqa: E712
                SysAiModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()

    # 2. 回退默认模型
    if not model:
        result = await db.execute(
            select(SysAiModel).where(
                SysAiModel.is_default == True,  # noqa: E712
                SysAiModel.status == True,  # noqa: E712
                SysAiModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()

    if not model:
        raise CustomError(
            err_code=CustomErrorCode.AGENT_NO_AVAILABLE_MODEL,
            msg=f"场景 [{function_code.value}] 未绑定模型且无可用默认模型",
        )

    try:
        api_key = decrypt_secret(model.api_key_encrypted)
    except Exception as e:
        logger.error("模型 %s 的 API Key 解密失败: %s", model.name, e)
        raise CustomError(
            err_code=CustomErrorCode.AGENT_MODEL_KEY_ERROR,
            msg=f"模型 [{model.name}] 的 API Key 解密失败",
        ) from e

    return ResolvedModel(model=model, api_key=api_key)


# ==================== 工具格式转换 ====================


def format_tools_for_provider(
    provider: AiProviderEnum, tools: list[dict]
) -> list[dict]:
    """
    把统一工具描述（OpenAI function 格式）转为各 provider 需要的格式。

    统一格式（也是 OpenAI 格式）:
        {"type": "function", "function": {"name", "description", "parameters"}}
    Anthropic 格式:
        {"name", "description", "input_schema"}
    """
    if not tools:
        return []

    if provider == AiProviderEnum.ANTHROPIC:
        result = []
        for t in tools:
            fn = t.get("function", t)
            result.append(
                {
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                }
            )
        return result

    # OpenAI 族直接返回
    return tools


def format_messages_for_provider(
    provider: AiProviderEnum, messages: list[dict]
) -> tuple[list[dict], str]:
    """
    把统一消息列表转为各 provider 需要的消息格式。

    统一格式兼容 OpenAI，非 Anthropic 直接返回 (messages, "")。
    Anthropic 需要把 system 消息提取到顶层，
    并把 tool 角色消息的 content 包装为 tool_result 块。

    返回 (provider 格式的消息列表, system 文本)。
    """
    if provider != AiProviderEnum.ANTHROPIC:
        return messages, ""

    system_text = ""
    converted: list[dict] = []

    for msg in messages:
        role = msg["role"]
        if role == "system":
            # 合并所有 system 消息
            content = msg.get("content") or ""
            if content:
                system_text += ("\n" if system_text else "") + content
            continue

        if role == "tool":
            # OpenAI 的 tool 消息 → Anthropic 的 user(tool_result) 块
            converted.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.get("tool_call_id", ""),
                            "content": msg.get("content", ""),
                        }
                    ],
                }
            )
            continue

        if role == "assistant" and msg.get("tool_calls"):
            # assistant 消息携带 tool_calls → Anthropic 的 content 块
            content_blocks: list[dict] = []
            if msg.get("content"):
                content_blocks.append({"type": "text", "text": msg["content"]})
            for tc in msg["tool_calls"]:
                # 兼容两种结构：内部精简格式 / OpenAI 完整格式
                if "function" in tc:
                    tc_id, tc_name = tc["id"], tc["function"]["name"]
                    tc_args = json.loads(tc["function"].get("arguments") or "{}")
                else:
                    tc_id, tc_name = tc["id"], tc["name"]
                    tc_args = tc.get("arguments", {})
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc_id,
                        "name": tc_name,
                        "input": tc_args,
                    }
                )
            converted.append({"role": "assistant", "content": content_blocks})
            continue

        converted.append({"role": role, "content": msg.get("content") or ""})

    return converted, system_text


# ==================== 流式调用 ====================


async def stream_chat(
    resolved: ResolvedModel,
    messages: list[dict],
    tools: Optional[list[dict]] = None,
    timeout: float = 120.0,
) -> AsyncGenerator[StreamChunk, None]:
    """
    流式调用 LLM，yield StreamChunk。

    - 文字增量 → chunk.content
    - 工具调用 → 累积到 chunk.tool_calls（同一轮可能多次 yield 增量，
      最终的 finish_reason='tool_calls' 时 tool_calls 完整）
    """
    model = resolved.model
    provider = model.provider

    if provider == AiProviderEnum.ANTHROPIC:
        async for chunk in _stream_anthropic(resolved, messages, tools, timeout):
            yield chunk
    else:
        async for chunk in _stream_openai_compatible(resolved, messages, tools, timeout):
            yield chunk


async def _stream_openai_compatible(
    resolved: ResolvedModel,
    messages: list[dict],
    tools: Optional[list[dict]],
    timeout: float,
) -> AsyncGenerator[StreamChunk, None]:
    """OpenAI / DeepSeek / Qwen / Zhipu / Custom 统一流式调用。"""
    model = resolved.model

    url = f"{model.base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {resolved.api_key}",
        "content-type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model.model_name,
        "messages": messages,
        "stream": True,
    }
    if model.temperature is not None:
        payload["temperature"] = model.temperature
    if model.max_tokens is not None:
        payload["max_tokens"] = model.max_tokens
    if tools:
        payload["tools"] = format_tools_for_provider(model.provider, tools)
        payload["tool_choice"] = "auto"

    # 累积工具调用的分片（index → {id, name, arguments_str}）
    tool_call_acc: dict[int, dict] = {}
    finish_reason: Optional[str] = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise CustomError(
                    err_code=CustomErrorCode.AGENT_LLM_REQUEST_FAILED,
                    msg=f"LLM 请求失败 HTTP {resp.status_code}: {body.decode()[:300]}",
                )

            async for line in resp.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue

                choices = obj.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})

                # 文字增量
                content = delta.get("content")
                if content:
                    yield StreamChunk(content=content)

                # 工具调用增量
                for tc_delta in delta.get("tool_calls", []):
                    idx = tc_delta.get("index", 0)
                    if idx not in tool_call_acc:
                        tool_call_acc[idx] = {
                            "id": "",
                            "name": "",
                            "arguments_str": "",
                        }
                    if tc_delta.get("id"):
                        tool_call_acc[idx]["id"] = tc_delta["id"]
                    fn = tc_delta.get("function", {})
                    if fn.get("name"):
                        tool_call_acc[idx]["name"] = fn["name"]
                    if fn.get("arguments"):
                        tool_call_acc[idx]["arguments_str"] += fn["arguments"]

                if choices[0].get("finish_reason"):
                    finish_reason = choices[0]["finish_reason"]

    # 流结束后，如果有工具调用，组装完整 tool_calls 一次性 yield
    if tool_call_acc:
        tool_calls = []
        for idx in sorted(tool_call_acc.keys()):
            acc = tool_call_acc[idx]
            try:
                args = json.loads(acc["arguments_str"]) if acc["arguments_str"] else {}
            except json.JSONDecodeError:
                args = {"_raw": acc["arguments_str"]}
            tool_calls.append(
                {"id": acc["id"], "name": acc["name"], "arguments": args}
            )
        yield StreamChunk(tool_calls=tool_calls, finish_reason=finish_reason or "tool_calls")
    else:
        yield StreamChunk(finish_reason=finish_reason or "stop")


async def _stream_anthropic(
    resolved: ResolvedModel,
    messages: list[dict],
    tools: Optional[list[dict]],
    timeout: float,
) -> AsyncGenerator[StreamChunk, None]:
    """Anthropic Claude 流式调用。"""
    model = resolved.model

    url = f"{model.base_url.rstrip('/')}/v1/messages"
    headers = {
        "x-api-key": resolved.api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # Anthropic 消息格式转换
    anthropic_messages, system_text = format_messages_for_provider(
        AiProviderEnum.ANTHROPIC, messages
    )

    payload: dict[str, Any] = {
        "model": model.model_name,
        "messages": anthropic_messages,
        "stream": True,
        "max_tokens": model.max_tokens or 4096,
    }
    if system_text:
        payload["system"] = system_text
    if model.temperature is not None:
        payload["temperature"] = model.temperature
    if tools:
        payload["tools"] = format_tools_for_provider(AiProviderEnum.ANTHROPIC, tools)

    # 累积工具调用（Anthropic 的 tool_use 在多个 event 中分片返回 input_json_delta）
    tool_acc: dict[str, dict] = {}  # tool_use_id → {name, input_str}

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise CustomError(
                    err_code=CustomErrorCode.AGENT_LLM_REQUEST_FAILED,
                    msg=f"LLM 请求失败 HTTP {resp.status_code}: {body.decode()[:300]}",
                )

            async for line in resp.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:]
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type", "")

                if event_type == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        yield StreamChunk(content=delta.get("text", ""))
                    elif delta.get("type") == "input_json_delta":
                        # 工具调用参数增量
                        partial = delta.get("partial_json", "")
                        # 需要找到当前正在累积的 tool_use block
                        # Anthropic 保证顺序：content_block_start 给出 index+tool_use，
                        # 随后的 input_json_delta 属于该 index
                        # 这里用最近一个未完成的 tool_acc 项
                        if tool_acc:
                            last_key = list(tool_acc.keys())[-1]
                            tool_acc[last_key]["input_str"] += partial

                elif event_type == "content_block_start":
                    block = event.get("content_block", {})
                    if block.get("type") == "tool_use":
                        tool_use_id = block.get("id", "")
                        tool_acc[tool_use_id] = {
                            "name": block.get("name", ""),
                            "input_str": "",
                        }

    # 组装完整 tool_calls
    if tool_acc:
        tool_calls = []
        for tool_use_id, acc in tool_acc.items():
            try:
                args = json.loads(acc["input_str"]) if acc["input_str"] else {}
            except json.JSONDecodeError:
                args = {"_raw": acc["input_str"]}
            tool_calls.append(
                {"id": tool_use_id, "name": acc["name"], "arguments": args}
            )
        yield StreamChunk(tool_calls=tool_calls, finish_reason="tool_calls")
    else:
        yield StreamChunk(finish_reason="stop")
