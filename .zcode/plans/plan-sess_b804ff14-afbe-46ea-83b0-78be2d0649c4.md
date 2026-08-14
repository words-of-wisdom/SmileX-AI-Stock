# Agent 模块实现方案

## 背景与目标

现有 LLM 配置系统已完成（多厂商凭据管理、场景绑定、连接测试），但**缺少真正调用 LLM 做事的业务层**——`AiFunctionEnum` 的 5 个场景只是枚举，没有对应的调用代码。

本方案实现一个**真正的 Agent**：支持流式对话 + 工具调用（Function Calling），让 LLM 能自主查询系统中的股票数据来回答用户问题。这是 Agent 和普通 Chatbot 的核心区别。

**实现策略**：MVP 优先，先把「LLM 配置 → 调用 → 流式输出 → 工具调用」完整链路跑通，预留场景扩展接口。

---

## 技术选型

| 决策点 | 方案 | 理由 |
|--------|------|------|
| LLM 调用 | **httpx 裸调**（不引入 openai SDK） | 与现有 `_do_ping()` 风格一致，零新依赖，厂商差异在 provider 层分派 |
| 流式通信 | **SSE (Server-Sent Events)** | 单向流式，比 WebSocket 轻量，天然适配 LLM token 流；FastAPI 原生 `StreamingResponse` 支持 |
| 前端流式消费 | **`@microsoft/fetch-event-source`** | 支持 POST + 自定义 header（需带 Authorization），比原生 EventSource 更灵活 |
| 工具调用 | **OpenAI Function Calling 格式** | 行业标准，DeepSeek/通义/智谱/custom 都兼容；Anthropic 走其原生 tool_use 格式（provider 层适配） |
| 依赖 | **仅新增前端 1 个包** | 后端零新依赖 |

---

## 后端实现（`backend/modules/agent/`）

### 1. 目录结构
```
backend/modules/agent/
├── __init__.py
├── router.py                    # 路由聚合 prefix=/admin/agent
├── endpoints/
│   ├── __init__.py
│   └── chat.py                  # POST /agent/chat（SSE 流式）
├── services/
│   ├── __init__.py
│   ├── llm_client.py            # 统一 LLM 调用封装（核心）
│   ├── agent_service.py         # Agent 编排（ReAct 循环）
│   └── tool_registry.py         # 工具注册表 + 调用分派
├── tools/                        # Agent 可调用的工具函数
│   ├── __init__.py
│   ├── stock_tools.py           # 股票相关工具（查行情、查热榜）
│   └── news_tools.py            # 新闻相关工具
└── schemas/
    ├── __init__.py
    └── chat.py                  # 请求/响应 Schema
```

### 2. 核心文件：`services/llm_client.py`
统一的 LLM 调用客户端，封装流式 + 非流式 + 工具调用：
- `resolve_model(db, function_code)` — 解析场景→模型（复用 `AiModelService` 的绑定+默认回退逻辑）
- `stream_chat(model, messages, tools=None)` → `AsyncGenerator[str, None]` — 流式对话，按 provider 分派请求格式（OpenAI 族 vs Anthropic），yield SSE 格式的 chunk
- `_call_openai_compatible(model, ...)` — OpenAI/DeepSeek/Qwen/Zhipu/Custom 统一走 `/chat/completions`，`stream=True`
- `_call_anthropic(model, ...)` — Anthropic 走 `/v1/messages`，`stream=True`，SSE event 格式适配
- `_format_tools_for_provider(provider, tools)` — 把统一工具描述转为各 provider 的 tool schema 格式
- `_parse_tool_calls(provider, response)` — 解析各 provider 返回的工具调用请求

关键设计：复用 `AiModelService` 已有的 `_do_ping` 中的 provider 分派模式和 `AI_PROVIDER_DEFAULT_BASE_URL`，保持风格一致。

### 3. 核心文件：`services/agent_service.py`
Agent 编排逻辑（ReAct 循环）：
```
async def run_agent_stream(db, messages, function_code, max_iterations=5):
    model = resolve_model(db, function_code)
    tools = tool_registry.get_openai_format()  # 注册的工具列表
    
    for iteration in range(max_iterations):
        # 1. 调用 LLM（流式）
        async for chunk in llm_client.stream_chat(model, messages, tools):
            if chunk.is_tool_call:
                break  # 收集完整 tool_call 后跳出流式
            yield format_sse("token", chunk.content)  # 推送文字给前端
        
        # 2. 如果 LLM 要求调用工具
        if tool_calls:
            for tc in tool_calls:
                yield format_sse("tool_call", tc)  # 推送工具调用信息给前端（可折叠展示）
                result = tool_registry.execute(tc.name, tc.arguments, db)
                yield format_sse("tool_result", result)  # 推送工具结果给前端
                messages.append(tool_result_message)  # 追加到对话历史
        
        # 3. 如果没有工具调用，说明 LLM 已给出最终回答，结束循环
        else:
            break
    
    yield format_sse("done", {})
```

### 4. 工具函数：`tools/stock_tools.py` + `tools/news_tools.py`
首期实现 3 个工具（验证链路 + 有实际价值）：

| 工具名 | 描述 | 数据来源 |
|--------|------|----------|
| `get_stock_quote` | 查询单只股票最新行情（价格、涨跌幅、成交量） | 复用 `StockHotService` / `MarketService` 查询逻辑 |
| `get_hot_stocks` | 获取当前热榜 Top N 股票 | 复用 `StockHotService.get_rank_list()` |
| `get_latest_news` | 获取最新财经新闻 | 复用现有 news 查询 |

工具用装饰器注册：
```python
@tool_registry.register(
    name="get_stock_quote",
    description="查询指定股票的最新行情数据",
    parameters={
        "type": "object",
        "properties": {
            "stock_code": {"type": "string", "description": "股票代码，如 000001"}
        },
        "required": ["stock_code"]
    }
)
async def get_stock_quote(db: AsyncSession, stock_code: str) -> dict:
    ...
```

### 5. SSE 端点：`endpoints/chat.py`
```python
@agent_router.post("/chat")
async def agent_chat(
    chat_in: AgentChatRequest,          # { function_code, messages, stream=True }
    db: AsyncSession = Depends(get_session),
    user: SysUser = Depends(current_user),
):
    """Agent 对话（SSE 流式响应）"""
    async def event_stream():
        async for event in AgentService.run_agent_stream(db, chat_in.messages, chat_in.function_code):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

SSE 事件格式（JSON）：
- `{"type": "token", "content": "分析"}` — LLM 生成的文字片段
- `{"type": "tool_call", "name": "get_stock_quote", "arguments": {...}}` — Agent 正在调用工具
- `{"type": "tool_result", "name": "get_stock_quote", "result": {...}}` — 工具返回结果
- `{"type": "done"}` — 本次对话结束
- `{"type": "error", "message": "..."}` — 错误

### 6. Schema：`schemas/chat.py`
```python
class ChatMessage(BaseReqEntity):
    role: Literal["user", "assistant", "system", "tool"]
    content: str | None
    tool_calls: list[dict] | None  # assistant 消息携带的工具调用

class AgentChatRequest(BaseReqEntity):
    function_code: AiFunctionEnum = Field(default=AiFunctionEnum.CHAT_QA)
    messages: list[ChatMessage]
    stream: bool = Field(default=True)
```

### 7. 路由注册
`router.py`:
```python
router = APIRouter(prefix="/admin/agent", tags=["AI Agent"])
router.include_router(chat_router)
```
在 `main.py` 加：
```python
from modules.agent.router import router as agent_router
# ...
app.include_router(agent_router)
```

---

## 前端实现

### 1. 新增依赖
```bash
cd frontend && pnpm add @microsoft/fetch-event-source
```

### 2. 类型定义：`src/typings/api/agent-chat.d.ts`
```ts
declare namespace Api {
  namespace AgentChat {
    type SSEEventType = 'token' | 'tool_call' | 'tool_result' | 'done' | 'error';
    interface SSEEvent {
      type: SSEEventType;
      content?: string;
      name?: string;
      arguments?: Record<string, any>;
      result?: any;
      message?: string;
    }
    interface ChatMessage {
      role: 'user' | 'assistant' | 'system';
      content: string;
      tool_calls?: { name: string; arguments: Record<string, any>; result?: any }[];
    }
    interface ChatRequest {
      function_code: string;
      messages: ChatMessage[];
      stream: boolean;
    }
  }
}
```

### 3. API 封装：`src/service/api/agent-chat.ts`
```ts
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { getAuthorization } from '@/service/request/shared';
import { getServiceBaseURL } from '@/utils/service';

const isHttpProxy = import.meta.env.DEV && import.meta.env.VITE_HTTP_PROXY === 'Y';
const { baseURL } = getServiceBaseURL(import.meta.env, isHttpProxy);

export function streamAgentChat(
  body: Api.AgentChat.ChatRequest,
  callbacks: {
    onToken: (text: string) => void;
    onToolCall?: (name: string, args: any) => void;
    onToolResult?: (name: string, result: any) => void;
    onDone?: () => void;
    onError?: (msg: string) => void;
  },
  signal?: AbortSignal
) {
  return fetchEventSource(`${baseURL}/admin/agent/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: getAuthorization(),
      'Accept-Language': getLocale()
    },
    body: JSON.stringify(body),
    signal,
    onmessage(ev) {
      const event: Api.AgentChat.SSEEvent = JSON.parse(ev.data);
      switch (event.type) {
        case 'token': callbacks.onToken(event.content || ''); break;
        case 'tool_call': callbacks.onToolCall?.(event.name!, event.arguments!); break;
        case 'tool_result': callbacks.onToolResult?.(event.name!, event.result); break;
        case 'done': callbacks.onDone?.(); break;
        case 'error': callbacks.onError?.(event.message || '未知错误'); break;
      }
    }
  });
}
```
在 `src/service/api/index.ts` 加 `export * from './agent-chat';`

### 4. 对话页面：`src/views/ai/chat/index.vue`
布局：左侧会话列表（首期可简化为单会话）+ 右侧消息流 + 底部输入框。
- 消息气泡：区分 user / assistant
- **工具调用折叠展示**：assistant 消息内的 `tool_calls` 以可折叠卡片形式展示（显示工具名、参数、结果摘要）——这是 Agent 区别于普通对话的视觉特征
- 流式打字效果：token 实时追加到当前 assistant 气泡
- 输入框：NInput textarea + 发送按钮（支持 Ctrl+Enter 发送）
- 停止生成：AbortController 中断 SSE
- Markdown 渲染：引入 `markdown-it`（如果项目已有则复用）渲染 LLM 回复

### 5. 路由与国际化
- elegant-router 自动生成路由（创建 `views/ai/chat/index.vue` 后）
- `zh-cn.ts` / `en-us.ts` 的 `route` 段加 `ai_chat: 'AI 对话'`
- `route.ai` 的 children 会自动包含 `ai_chat`
- 页面级 i18n 加 `page.aiChat.*` 键

### 6. 菜单注册（Alembic 迁移）
新建迁移 `0014_add_ai_chat_menu.py`，在「AI助手」目录下添加「AI 对话」菜单项（参照 `0009_seed_ai_model_menu.py` 的模式）。

---

## 实现步骤（按顺序执行）

### Step 1：后端 LLM 客户端
1. 创建 `backend/modules/agent/` 目录骨架
2. 实现 `services/llm_client.py`（stream_chat + provider 分派 + tool_call 解析）
3. 实现 `schemas/chat.py`

### Step 2：后端 Agent 编排 + 工具
4. 实现 `services/tool_registry.py`（注册装饰器 + execute 分派）
5. 实现 `tools/stock_tools.py`（3 个工具）
6. 实现 `services/agent_service.py`（ReAct 循环 + SSE 格式化）

### Step 3：后端端点 + 路由
7. 实现 `endpoints/chat.py`（SSE StreamingResponse）
8. 实现 `router.py` + 注册到 `main.py`

### Step 4：前端流式 API + 页面
9. 安装 `@microsoft/fetch-event-source`
10. 实现 `typings/api/agent-chat.d.ts` + `service/api/agent-chat.ts`
11. 实现 `views/ai/chat/index.vue`（对话 UI + 工具调用展示 + 流式渲染）
12. 补充 i18n 键

### Step 5：菜单 + 文档
13. Alembic 迁移：AI 对话菜单
14. 更新 `aiDoc/memory/business/` 记录本次需求
15. 更新 `aiDoc/frontend-backend/boundary.md`（前后端契约）

---

## 关键设计决策

1. **不引入 LangChain/LlamaIndex**：这些框架对当前需求过重，且引入大量隐式行为。项目现有风格是轻量 httpx 裸调，Agent 循环逻辑简单（<100 行），自己实现更可控。

2. **复用现有 LLM 配置**：Agent 调用时通过 `function_code` 解析模型（绑定优先 → 默认回退），完全不改动现有 `ai_model` 表和服务，只读取。

3. **工具调用走 OpenAI Function Calling 格式**：统一接口，provider 层适配差异。首期工具直接查询现有 DB（复用 stock/news service），不引入外部数据源。

4. **会话历史暂不持久化**：首期对话历史存前端（localStorage 或内存），降低复杂度。后续如需持久化再加 `agent_conversation` 表。

5. **Anthropic 适配**：Anthropic 的 tool_use 格式与 OpenAI 不同，在 `llm_client.py` 的 provider 分派层统一转换，对上层 Agent 编排透明。