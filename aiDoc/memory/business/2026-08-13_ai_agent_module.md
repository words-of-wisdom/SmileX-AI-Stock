# 2026-08-13 AI Agent 模块

## 背景

现有 LLM 配置系统已完成（多厂商凭据管理、场景绑定、连接测试），但 `AiFunctionEnum` 的 5 个场景（智能选股/舆情分析/新闻摘要/对话问答/趋势预测）只是枚举，没有对应的调用代码。用户需要一个真正的 Agent 来操控 LLM 做分析。

## 需求

实现 AI Agent 模块，让 LLM 能通过 Function Calling 自主查询系统中的股票数据来回答用户问题，而非简单的 Chatbot。

## 实现方案

### 核心架构
- **不引入 LangChain/LlamaIndex**，用 httpx 裸调（与现有 `_do_ping` 一致），零后端新依赖
- **SSE 流式通信**：FastAPI `StreamingResponse`，前端用 `@microsoft/fetch-event-source`
- **OpenAI Function Calling 格式**为统一标准，Anthropic 在 provider 层适配
- **ReAct 循环**：LLM 思考 → 工具调用 → 结果反馈 → 最终回答（最大 8 轮）

### 后端 `backend/modules/agent/`
- `services/llm_client.py`：统一 LLM 调用客户端
  - `resolve_model(db, function_code)`：场景绑定优先 → 默认回退（复用 `sys_ai_model` 表）
  - `stream_chat(resolved, messages, tools)`：按 provider 分派（OpenAI 族 `/chat/completions` vs Anthropic `/v1/messages`）
  - `format_tools_for_provider` / `format_messages_for_provider`：provider 适配
- `services/tool_registry.py`：`@register_tool` 装饰器注册 + `execute()` 分派
- `services/agent_service.py`：`AgentService.run_agent_stream()` ReAct 循环，yield SSE 事件
- `tools/stock_tools.py`：6 个工具
  - `get_hot_stocks`：股票热榜（复用 StockHotService）
  - `get_market_indices`：大盘指数行情（复用 MarketService）
  - `get_market_fund_flow`：大盘资金流向（复用 MarketService）
  - `get_board_ranking`：行业/概念板块排行（复用 BoardService）
  - `get_limit_up_stocks`：涨停股池（复用 LimitUpService）
- `tools/news_tools.py`：`get_latest_news`（直接查 BusinessNews 表）
- `endpoints/chat.py`：`POST /admin/agent/chat` SSE 流式响应
- `schemas/chat.py`：AgentChatRequest / ChatMessage / ToolCallInfo

### SSE 事件格式
- `{"type": "token", "content": "..."}` — LLM 文字增量
- `{"type": "tool_call", "id", "name", "arguments"}` — 正在调用工具
- `{"type": "tool_result", "id", "name", "result"}` — 工具执行结果
- `{"type": "done"}` — 结束
- `{"type": "error", "message"}` — 错误

### 前端 `frontend/src/views/ai/chat/`
- `index.vue`：对话主页面（消息流 + 输入框 + 流式打字效果 + 停止生成）
- `modules/tool-call-card.vue`：工具调用可折叠卡片（Agent 视觉特征）
- `service/api/agent-chat.ts`：`streamAgentChat()` 封装 fetch-event-source
- `typings/api/agent-chat.d.ts`：SSEEvent / ChatMessage / StreamCallbacks

### 其他
- 新增错误码号段 11301-11400（Agent 相关）
- Alembic 迁移 `0014_add_ai_chat_menu.py`：AI助手目录下新增「AI 对话」菜单（ID 2942406616008007）
- 新增前端依赖：`@microsoft/fetch-event-source` + `markdown-it`
- i18n：`route.ai_chat` = 'AI 对话' / 'AI Chat'
- 系统提示词内置在 `agent_service.py` 的 `SYSTEM_PROMPT`

## 设计决策

1. **会话历史暂不持久化**：首期对话历史存前端内存，后续如需持久化再加 `agent_conversation` 表
2. **SSE 不走统一响应包装**：SSE 是流式，错误信息通过 `error` 事件传递，不走 `{ code, msg, data }`
3. **系统提示词硬编码**：Agent 角色设定写死在代码中，后续可考虑迁移到 DB 配置
4. **Anthropic 适配在 provider 层**：tool_use ↔ function calling 格式转换对上层透明
5. **无单只个股行情工具**：现有系统无个股行情 service，用热榜/涨停数据替代

## 扩展方向
- 新增工具：只需在 `tools/` 下用 `@register_tool` 装饰器添加，自动出现在工具列表
- 新增场景：`AiFunctionEnum` 已有 5 个场景，通过场景绑定不同模型即可
- 会话持久化：后续可加 conversation/message 表
- 多模态：llm_client 层可扩展图片输入支持
