# 策略执行异步化 + 每分钟模拟交易引擎

## 根因与现状

**问题1（超时）**：`POST /admin/strategy/strategies/{id}/run`（endpoints/strategy.py:115）在 HTTP 请求内同步 await `StrategyExecutor.run` —— 最多 8 轮 LLM 流式调用（每轮 httpx 各类超时 120s 且不限总时长）+ 工具外部请求 + 新浪行情拉取，轻松超过 gunicorn/nginx 的 120s 超时。

**问题2（立即买卖）**：`_apply_signals`（strategy_executor.py:312）在 LLM 分析完成后立即建仓/平仓。

**改造核心**：① 执行记录落库后立即返回，LLM 分析转后台任务；② 分析只产出"待执行信号"（新表），由新增的每分钟"模拟交易引擎"任务拉取行情并执行模拟买卖 + 接管原每 5 分钟持仓跟踪。

已按推荐决策：合并为一个每分钟任务；未执行信号次日收盘后作废、且被同策略新信号替换；买入按下一分钟实时市价成交。

## 一、数据库迁移（新建 `backend/alembic/versions/0020_strategy_async_run_and_signals.py`）

1. **`business_strategy_run.status`**：`Boolean` → `String(20)`，数据迁移 `USING CASE WHEN status THEN 'success' ELSE 'failed' END`，新默认 `'running'`（running/success/failed 三态，bool 无"执行中"语义）
2. **新表 `business_strategy_signal`**（待执行信号）：
   - `strategy_id` BigInteger 索引、`strategy_name` String(100)、`run_id` BigInteger、`run_period` String(20)、`run_date` String(10)
   - `stock_code` String(20) 索引、`stock_name` String(50)、`action` String(10)（buy/sell/adjust，hold 不落表）
   - `ref_buy_price`/`target_sell_price`/`stop_loss_price` Numeric(16,4) 可空、`reason` String(500) 可空
   - `status` String(20) 索引（pending/executed/skipped/failed/expired，默认 pending）
   - `executed_at` DateTime 可空、`executed_price` Numeric(16,4) 可空、`result_msg` String(500) 可空
   - 复合索引 `(strategy_id, status)`、`(run_id)`
3. **下线旧任务**：`UPDATE sys_scheduled_task SET deleted_at=now() WHERE task_key='strategy.position_track' AND deleted_at IS NULL`（sync_jobs_from_db 只加载未软删任务，重启后自动不再调度）

## 二、后端 strategy 模块

### 1. `database/models/business/strategy.py`
- `BusinessStrategyRun.status` 改 `Mapped[str]`（默认 "running"）
- 新增 `BusinessStrategySignal` 模型（字段同上表）

### 2. `services/strategy_executor.py` 重构
- 新增 `submit_run(db, strategy, run_period, trigger_type) -> int`：
  - 并发守卫：该策略已存在 `status="running"` 记录 → 抛 `CustomError`（新错误码 `STRATEGY_ALREADY_RUNNING = (11508, ...)` + 后端 i18n）
  - 创建 `status="running"` 的 Run 记录、更新 `strategy.last_executed_at`、commit，立即返回 run_id
  - `asyncio.create_task(_execute_analysis(run_id, strategy_id, run_period, trigger_type))`，模块级 `set` 持引用 + done callback 丢弃（防 GC）
- `_execute_analysis`：**独立 session**（`get_session()`，只传 id 不传 ORM 实例）；重载 strategy → 持仓 → LLM → 解析信号；**不再调用 `_apply_signals`**，改为：同策略旧 pending 信号置 `expired` → 写入新 pending 信号（buy/sell/adjust）→ `run.status="success"`；失败置 `failed` + error_msg（保留现有 rollback 前缓存 id/name 的 MissingGreenlet 规避写法）；整体包 `asyncio.wait_for` 600s 兜底超时
- 删除 `_apply_signals`（逻辑移入交易引擎，按单信号粒度改造）

### 3. 新增 `services/trade_engine.py`：`TradeEngine.execute_tick(db)`
1. **僵死恢复**：`running` 超 15 分钟的 Run → `failed`（"执行超时（进程重启或异常中断）"）
2. **信号过期**：`now ≥ 15:05` 时将 `run_date < today` 的 pending 信号置 `expired`（次日收盘作废；盘后信号次日仍可执行）
3. **交易时段检查**：非 9:30-11:30 / 13:00-15:00（周一至周五）直接返回
4. 加载 pending 信号（策略已停用/删除的 → `expired`）+ holding 持仓，`codes = 信号股 ∪ 持仓股` **一次** `fetch_latest_prices` 批量拉价
5. **执行信号**（每条独立更新状态）：buy → 实时价建仓（满仓/无价格 → `skipped` + result_msg）；sell → 实时价平仓（`sell_reason="ai_signal"`）；adjust → 更新目标价/止损价；成交后累加来源 Run 的 `opened_count`/`closed_count`
6. **持仓跟踪**：刷新 `latest_price`/`floating_pnl_pct` + 止损/目标价自动平仓 + track_log（复用现有逻辑）

### 4. `services/position_service.py`
`track_positions(db, prices=None)` 增加可选外部价格参数（引擎传入避免重复拉价；`POST /positions/track` 手动接口行为不变）

### 5. `schemas/strategy.py` + `endpoints/strategy.py`
- `StrategyRunItem.status: str`；`StrategyRunResult` 替换为 `StrategyRunSubmitResult {run_id: int, status: str = "running"}`
- `/run` 端点改为调 `submit_run`，**毫秒级返回** `msg="已提交执行"`（Swagger summary 同步更新）

## 三、调度任务 `modules/scheduler/tasks/strategy_run.py`
- `strategy_run_execute`（*/10）：去重逻辑不变（running 记录参与去重），命中后改调 `submit_run` 非阻塞提交，任务本身秒回，不再受任务级 300s 超时影响
- **新增** `strategy.trade_engine`：`@scheduled_task(cron="* * * * * 9-15 * * mon-fri", is_system=True)`，调 `TradeEngine.execute_tick`（星期必须 mon-fri，APScheduler 周一=0 的坑已在文件头注释）
- 删除 `strategy_position_track` 任务（DB 行由迁移软删；新任务行由启动 `sync_registry_to_db` 自动创建）
- `main.py` 无需改动（同文件已被 import）

## 四、前端
- `typings/api/strategy.d.ts`：`StrategyRunItem.status: 'running'|'success'|'failed'`；`StrategyRunResult` → `{run_id: number; status: string}`
- `views/ai/analysis/index.vue`：
  - `onRunStrategy`：改为提交即提示"已提交执行，结果请查看执行记录"，并刷新执行记录列表
  - run 状态列三态渲染：running（info 色标签）/ success / failed
- `locales/langs/zh-cn.ts`、`en-us.ts`：新增 `runSubmitted`、`execRunning` 等 key
- `service/api/strategy.ts`：`fetchRunStrategy` 泛型类型同步

## 五、文档与记忆（AGENTS.md 要求）
- `aiDoc/memory/business/` 新增本次需求记忆 + 更新需求索引
- Run status 布尔→字符串属跨栈契约变更，检查并同步 `aiDoc/frontend-backend/` 相关文档

## 验证
1. `alembic upgrade head`（注意 memory 中 alembic 坑：运行中不 downgrade）
2. 重启后端：`sys_scheduled_task` 自动出现 `strategy.trade_engine`、`strategy.position_track` 已软删
3. 调 `/run`：立即返回 run_id；执行记录出现 running → success；`business_strategy_signal` 出现 pending 记录；不再有即时持仓变动
4. 手动触发 trade_engine 任务（或等到整分钟）：信号被执行/跳过并留痕，持仓生成、Run 计数更新、持仓价刷新、止损止盈正常
5. 前端：执行按钮即时反馈、三态状态标签正常（zh/en）
6. 后端语法检查 + 前端 type check