# 2026-08-16 AI 分析策略模块

## 需求

用户提出：新增「AI 分析」板块，支持定制各种策略；每个策略可在不同时间执行（如早盘策略等）；记录每个策略给出的买点并预估卖点；不断跟踪每个个股的操作情况，以此计算回报率。

## 方案（经确认采用）

- **AI 驱动**：策略执行复用 agent 模块 LLM 层（`llm_client.resolve_model/stream_chat` + `tool_registry`），场景绑定复用 `AiFunctionEnum.STOCK_PICKING`（未新增枚举值，避免 PG enum 迁移）；要求 LLM 输出严格 JSON 信号数组（buy/sell/adjust/hold + 买点/目标卖点/止损价/理由）
- **预设时段**：策略配置多选执行时段（pre_market 9:15-9:25 / morning 9:30-11:30 / noon 13:00-14:30 / tail 14:30-15:00 / post_close 15:05-16:00），不开放自定义 cron
- **模拟盘自动跟踪**：AI 买点自动建仓（按新浪实时价定价），定时任务刷新最新价/浮盈，触发止损/达到预估卖点自动平仓并计算收益率；支持手动平仓
- **一期前后端完整交付**

## 实现

### 后端 `backend/modules/strategy/`（前缀 `/admin/strategy`）

- 4 张表（`database/models/business/strategy.py`）：`business_ai_strategy`（策略配置）、`business_strategy_run`（执行记录，含 AI 原文+解析信号，run_date+run_period 去重）、`business_strategy_position`（模拟持仓：买点/预估卖点/止损/最新价/浮盈/return_rate）、`business_position_track_log`（跟踪日志）
- `strategy_service.py` CRUD；`strategy_executor.py` 核心：系统提示词要求 JSON 数组 → ReAct 工具循环（复用 agent 6 工具）→ `_extract_json_array` 容错解析（```json 代码块/[..]区间）→ 应用信号（buy 受 max_positions 限制、sell 平仓、adjust 调目标价）；`quote_helper.py` 6位代码→新浪 sh/sz/bj 前缀批量取最新价；`position_service.py` 跟踪/平仓/统计（胜率/累计/平均收益率）
- 调度 `scheduler/tasks/strategy_run.py`：`strategy.run_execute` cron `*/10 9-16 * * mon-fri`（时段窗口匹配+同日同时段去重）、`strategy.position_track` cron `*/5 9-15 * * mon-fri`（交易时段守卫）；沿用 mon-fri 星期坑规避
- 错误码 11501-11507（STRATEGY_*/POSITION_*）；迁移 `0015`（4 表 + AI 助手目录下「AI 分析」菜单 8008 + 按钮 strategy:manage/run/position:close，菜单权限 strategy:position:list）

### 前端 `views/ai/analysis/`

- 三 Tab：策略管理（分页表格 + 配置抽屉：提示词/股票池/时段多选/止损止盈）、持仓跟踪（holding/closed 筛选、红涨绿跌浮盈、手动平仓、立即跟踪、60s 自动刷新）、回报率统计（汇总卡片 + 按策略胜率/收益率表）
- 执行记录抽屉（信号明细 buy/sell/adjust 标签）
- API `service/api/strategy.ts` + 类型 `typings/api/strategy.d.ts`；路由 elegant-router 自动生成 `ai_analysis`；i18n `page.aiStrategy.*`（zh/en）+ `src/typings/app.d.ts` Schema 手工同步（该文件是手维护的 I18nKey 真源！）

## 注意点 / 坑

- `src/typings/app.d.ts` 的 i18n Schema 是**手工维护**的，新增 i18n key 必须同步该文件，否则 vue-tsc 报 I18nKey 不匹配
- FastAPI include_router 不允许 prefix 与 path 同时为空，strategy CRUD 路由用了前缀 `/strategies`
- 模型 dataclass（Base=MappedAsDataclass）字段有默认值后不能再跟无默认值字段（BusinessStrategyRun.status 需 default）
- LLM JSON 解析失败不抛异常，记入 Run.error_msg；建仓价优先新浪实时价，取不到用 AI 给的 buy_price
- 收益率口径：等权按笔加总（未含复利/仓位权重）；买入按信号触发时最新价一手模拟，无滑点建模

## 后续可扩展

- 规则引擎策略类型（预留 status 字段之外可在表加 strategy_type）
- 卖点预估由跟踪任务中再次询问 LLM 调整（当前 adjust 仅在策略执行时更新）
- 收益曲线 ECharts 图表
