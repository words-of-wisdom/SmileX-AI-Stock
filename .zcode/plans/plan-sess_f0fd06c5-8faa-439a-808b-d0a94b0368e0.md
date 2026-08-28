# 任务1：持仓跟踪页改造

## A. 修复无法滚动
**根因**：`frontend/src/views/ai/analysis/index.vue:707-708` 外层 `overflow-hidden` + NCard `sm:flex-1-hidden`，而 NDataTable 未设 `flex-height`，内容超高被直接裁剪。
**修复**：给持仓 Tab 的 `NDataTable` 加 `flex-height` 并保证 NCard body 形成确定高度的 flex 链（参照项目内其他表格页的写法），使表格内部可纵向滚动；`scroll-x=1550` 保留横向滚动。

## B. 策略筛选（前端）
- `strategy_id` 状态已存在（L383-387）但无 UI。加一个 NSelect（filterable，clearable），选项来自已有的策略列表接口（同页策略 Tab 已加载）。
- 后端 `GET /positions` 已支持 `strategy_id` 参数，无需后端改动。

## C. 时间段筛选（前后端）
- 后端 `backend/modules/strategy/endpoints/position.py` + `services/position_service.py:109-143`：新增 `start_time` / `end_time` 查询参数，按 `buy_time` 过滤（datetime 解析，非法/空返 None，遵循 Annotated+BeforeValidator 模式防 422）。
- 前端加 NDatePicker（datetimerange，clearable），传参给 `fetchPositions`；同步更新 `frontend/src/service/api/strategy.ts` 与 `typings/api/strategy.d.ts`。

## D. 盈亏排序（前后端）
- 后端 `get_positions` 排序目前硬编码（holding 前置 + buy_time desc）。新增 `sort_by`（如 `pnl` / `buy_time` / `return_rate`，白名单枚举）与 `sort_desc` 参数；holding 前置逻辑保留为默认。
- 前端浮动盈亏/收益率/买入时间列加 `sorter`，走后端排序（非本地排序，因分页在服务端）。
- 注意 schema、Swagger 注释与实际行为一致。

## E. 文档与记忆
- 按 AGENTS.md 同步 `aiDoc/frontend-backend/` 契约、新增 business 记忆一条。

# 任务2：亏损归因分析（结论 + 数据验证）

## 代码层结论
1. **执行价格不是问题**：trade_engine 每分钟 tick 直接实时调新浪行情（`quote_helper.py`，无缓存无 DB 中间层），执行延迟最多 1 分钟。
2. **真正的数据时效错位在信号生成侧**：AI 分析用的 get_market_indices/get_board_ranking/get_limit_up_stocks 等工具读的是 **每日 15:30-15:40 收盘后同步的 DB 快照**（`stock_market_sync.py`），盘中跑的策略看到的是**昨日**大盘/板块/涨停数据；只有热榜是 5 分钟级新鲜。AI 基于过期市场环境选股，可能是亏损主因之一。
3. **T+1 结构性风控缺口**：当日买入的持仓止损/止盈均不触发（`position_service.py:81`），买入当日暴跌无法止损——若亏损集中在建仓当日，原因在此而非数据延迟。
4. **价格位历史 bug 已修但有残留风险**：_sanitize_price_levels 已做方向校验，但仍依赖策略 pct 兜底。

## 实施时将执行的验证（只读 SQL）
- 按平仓原因分组统计 avg/min return_rate（亏损是否集中在 stop_loss）
- 统计亏损单中"当日买入当日平仓/买入首日最大跌幅"占比（验证 T+1 缺口影响）
- 抽查 `business_position_track_log` 价格连续性 + `sys_scheduled_task_log` 同步任务成功率
- 对比信号 `ref_buy_price` 与 `executed_price` 偏差

## 可选后续改进（验证后决定，本次不做）
- 信号生成时改为直拉实时行情而非读昨日快照
- T+1 期间允许"记录但不能卖"改为盘中风控前置（信号侧过滤高风险标的）

验证结论将单独汇报，若确认是数据时效问题，再讨论修复方案。