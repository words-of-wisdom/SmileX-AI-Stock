# 策略执行异步化 + 每分钟模拟交易引擎

## 需求描述

1. 修复启动策略超时：手动执行 `POST /strategies/{id}/run` 在 HTTP 请求内同步跑完 LLM ReAct 循环（最多 8 轮流式 LLM + 工具调用，httpx 单轮不设总时长上限），轻松超过 gunicorn/nginx 120s 超时
2. 执行策略时不立即买卖：新增每分钟定时任务拉取策略股票实时行情，按实时价执行模拟买卖操作

## 状态

已完成

## 涉及范围

### 后端

- `business_strategy_run.status`：Boolean → String(20) 三态（running/success/failed），迁移 0020 `USING CASE WHEN status THEN 'success' ELSE 'failed' END`
- 新表 `business_strategy_signal`（待执行信号）：LLM 分析只产出信号不买卖，`status` pending/executed/skipped/failed/expired；同策略新一轮分析作废旧 pending（expired"被替换"）；收盘后 15:05 作废 run_date < 今日 的滞留信号（盘后信号次日仍可执行）
- `StrategyExecutor` 重构：`submit_run`（并发守卫 + 创建 running 记录 + `asyncio.create_task` 后台分析，模块级 set 持引用防 GC）+ `_execute_analysis`（独立 session 只传 id、`asyncio.wait_for` 600s 兜底、失败回写 failed）；删除 `_apply_signals`
- 新增 `services/trade_engine.py`：`TradeEngine.execute_tick` 每分钟 tick —— 僵死 running 记录恢复（>15min 置 failed）→ 信号过期 → 交易时段判断（9:30-11:30/13:00-15:00）→ 信号+持仓一次批量拉价（新浪）→ 执行信号（先卖后买再调整，停牌缺价保持 pending 重试，满仓/无持仓 skipped）→ 累加来源 run 的 opened/closed 计数 → 持仓跟踪（止损/止盈/目标价自动平仓）
- 调度任务：`strategy.run_execute`（*/10）改非阻塞 submit；新增 `strategy.trade_engine`（`* * * * * 9-15 * * mon-fri`）；下线 `strategy.position_track`（*/5，迁移中软删 sys_scheduled_task 行，职责并入交易引擎）
- `PositionService.track_positions` 加 `prices` 可选参数（引擎传入避免重复拉价）
- 错误码新增 `STRATEGY_ALREADY_RUNNING = 11508`

### 前端

- `views/ai/analysis/index.vue`：执行按钮改"已提交"提示（刷新策略列表 + 打开中的执行记录抽屉）；run 状态列三态标签（running=info/success/failed）
- 类型：`StrategyRunItem.status: 'running'|'success'|'failed'`；`StrategyRunResult` 简化为 `{run_id, status}`
- i18n：`runSuccess/runFailed` 移除，新增 `runSubmitted/execRunning`（app.d.ts 手工同步）

## 约束与备注

- 买入按下一分钟实时市价成交（不设限价）；hold 信号不落表
- 后台分析只传 id 不传 ORM 实例（跨 session）；失败回写用裸 UPDATE 不访问过期属性（MissingGreenlet 规避）
- `sync_registry_to_db` 只 upsert 不删行，退役任务必须在迁移里软删 DB 行
- 新任务行由启动 seed 自动入库，无需迁移种子

## 相关文件

- backend/alembic/versions/0020_strategy_async_run_and_signals.py
- backend/modules/strategy/services/strategy_executor.py、trade_engine.py、position_service.py
- backend/modules/scheduler/tasks/strategy_run.py
- frontend/src/views/ai/analysis/index.vue、src/typings/api/strategy.d.ts

## 记录日期

2026-08-18
