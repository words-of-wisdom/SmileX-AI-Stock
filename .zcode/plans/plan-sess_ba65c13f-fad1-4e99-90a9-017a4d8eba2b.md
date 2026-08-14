# 暗盘跟踪模块 实现方案

## 背景与数据源澄清

东方财富网**没有**公开的「暗盘」榜单接口。在 A 股语境中，「暗盘」通常非正式地指代**大宗交易**（盘后场外撮合，本质是 dark pool），其公开数据来源即东方财富数据中心「大宗交易」板块（`data.eastmoney.com/dzjy/`）。akshare 的 `stock_dzjy_*` 系列接口正是抓取该数据源（已验证可用，akshare `1.18.83`）。

因此本模块的「暗盘跟踪」= **大宗交易跟踪**，数据源为东方财富（经 akshare）。共纳入两个「榜单型」子榜：
- **每日统计**（`stock_dzjy_mrtj`）：按个股聚合的每日大宗交易排行，含成交价/折溢率/成交总额/占流通市值比，**主榜单**
- **活跃A股统计**（`stock_dzjy_hygtj`）：近一月/三月/六月/一年内大宗交易上榜次数最多的个股排行，**次榜单（按时间窗口切换）**

> 不纳入「每日明细」（逐笔明细，非榜单）和「营业部排行」（与个股暗盘语义偏离），保持聚焦。

## 设计要点

- **完全复用现有 stock 模块模式**：参照 `stock_hot`（多源 fetcher + service + 同步日志表 + 排名对比）和 `limit_up`（单表快照 + 日期回看 + stats）。本模块两个子榜结构不同，拆成**两张快照表**（每日统计 / 活跃统计），共用一张同步日志表。
- **复用 `_common.py`**：`num()` / `normalize_code()` / `derive_market_board()`。
- **权限命名**：`stock:block_trade:list` / `:sync` / `:view`（与 `stock:limit_up:*`、`stock:board:*` 一致的 `stock:<slug>:<action>` 模式）。
- **调度**：大宗交易数据在收盘后才稳定，cron 定 `40 15 * * mon-fri`（15:40，晚于现有涨停同步 15:35，避开高峰）。手工同步接口同步保留。
- **菜单**：挂在已存在的「A股」一级目录（id `2942406616009001`）下，sort 取 5（现有 market-overview=1, industry-board=2, limit-up=3, stock-hot=4）。

## 文件清单（共 16 处变更）

### 后端（10 处）

1. **`backend/database/models/business/block_trade.py`**（新建）
   - `BusinessBlockTradeDaily`：每日统计快照表。唯一键 `(record_date, stock_code)`。字段：record_date, stock_code, stock_name, change_pct, close_price, trade_price, premium_rate(折溢率), trade_count(笔数), trade_volume(总量), trade_amount(总额,万元), amount_ratio(占流通市值%)。
   - `BusinessBlockTradeActive`：活跃A股统计表。唯一键 `(stat_window, stock_code)`，`stat_window` ∈ {'近一月','近三月','近六月','近一年'}。字段：stat_window, stock_code, stock_name, latest_price, change_pct, last_list_date(最近上榜日), list_count_total, list_count_premium, list_count_discount, total_amount, premium_rate, amount_ratio, avg_change_1d/5d/10d/20d。
   - `BusinessBlockTradeSyncLog`：采集日志（复用 stock_hot 同步日志结构，含 stat_window 字段区分两个子榜）。

2. **`backend/database/models/business/__init__.py`**（改）：导出新模型。

3. **`backend/modules/stock/schemas/block_trade.py`**（新建）：`BlockTradeDailyItem` / `BlockTradeActiveItem` / `BlockTradeSourceItem` / `BlockTradeHistoryItem`，均继承 `BaseEntity`。

4. **`backend/modules/stock/services/block_trade_fetcher.py`**（新建）：`fetch_daily(client, start_date, end_date)` 调 `stock_dzjy_mrtj`；`fetch_active(client, window)` 调 `stock_dzjy_hygtj`。返回标准化 dict 列表，复用 `_common.num` / `normalize_code`。

5. **`backend/modules/stock/services/block_trade_service.py`**（新建）：`BlockTradeService` 类，`@staticmethod`：
   - `sync_daily(db, date)` / `sync_active(db, window)` / `sync_all(db)`：PG `insert ... on_conflict_do_update` upsert（按唯一键），写 SyncLog，逐子榜 commit/rollback 隔离失败。
   - `get_daily_list(db, date)`：含「占流通市值比」排名对比（与上一交易日对比排名变化，复用 stock_hot 的 prev_map 思路）。
   - `get_active_list(db, window)`。
   - `get_sources(db)` / `get_dates(db)` / `get_history(db, stock_code, days)`。

6. **`backend/modules/stock/endpoints/block_trade.py`**（新建）：`block_trade_router`，prefix `/block-trade`，tag「系统管理/暗盘跟踪」。接口：`POST /sync`、`GET /sources`、`GET /daily-list`、`GET /active-list`、`GET /dates`、`GET /history`。每个接口挂 `require_permission("stock:block_trade:*")`。

7. **`backend/modules/stock/endpoints/__init__.py`**（改）：导出 `block_trade_router`。

8. **`backend/modules/stock/router.py`**（改）：`router.include_router(block_trade_router)`。

9. **`backend/modules/scheduler/tasks/stock_block_trade_sync.py`**（新建）：`@scheduled_task(cron="40 15 * * mon-fri", task_key="stock.block_trade_sync", is_system=True)`，调用 `BlockTradeService.sync_all`。

10. **`backend/main.py`**（改）：第 67 行后加 `import modules.scheduler.tasks.stock_block_trade_sync  # noqa: F401`。

11. **`backend/alembic/versions/0013_add_block_trade_module.py`**（新建，down_revision='0012'）：
    - 建 3 张表（含索引/唯一约束/注释）。
    - `bulk_insert sys_menu`：1 个 MENU（`a-stock_block-trade`）+ 2 个 BUTTON（`stock:block_trade:list` / `stock:block_trade:sync`），parent = `_A_STOCK_DIR_ID`，ID 取 `2942406616009011~9013`（紧接 limit-up 的 9010）。
    - `downgrade()` 反向删表 + 删菜单。
    - 生成命令：`uv run alembic revision --autogenerate -m "add block trade module"` 后手工补菜单 bulk_insert 段，再 `uv run alembic upgrade head`。

### 前端（5 处）

12. **`frontend/src/typings/api/block-trade.d.ts`**（新建）：`namespace Api.BlockTrade`，含 `BlockTradeDailyItem` / `BlockTradeActiveItem` / `BlockTradeSourceItem` / `BlockTradeHistoryItem`。

13. **`frontend/src/service/api/block-trade.ts`**（新建）：`fetchGetBlockTradeSources` / `fetchGetBlockTradeDailyList` / `fetchGetBlockTradeActiveList` / `fetchGetBlockTradeDates` / `fetchGetBlockTradeHistory` / `fetchSyncBlockTrade`。并在 `frontend/src/service/api/index.ts` 加 `export * from './block-trade';`。

14. **`frontend/src/views/a-stock/block-trade/index.vue`**（新建）：以 `limit-up/index.vue` 为骨架。
    - 顶部：活跃度窗口单选切换（近一月/三月/六月/一年）—— 仅当切到「活跃榜」tab 时显示；主视图默认「每日统计」。
    - 用 `NDataTable` 展示榜单，复用 `a-stock/utils.ts` 的 `stockChangeColor` / `fmtFixed` / `fmtMoney` / `fmtSignedMoney` / `isStockAutoRefreshTime`。
    - 头部工具栏：最后刷新时间 + 日期选择器（gated by availableDates）+ 同步按钮 + 刷新按钮。
    - `useAutoRefresh(..., { shouldRefresh: isStockAutoRefreshTime })`。
    - 列：排名、股票名称(带代码+跳转雪球)、收盘价、成交价、折溢率(着色)、成交笔数、成交总额(fmtMoney)、占流通市值%(进度条)。

15. **`frontend/src/locales/langs/zh-cn.ts` + `en-us.ts`**（改）：
    - 路由标题：`'a-stock_block-trade': '暗盘跟踪'` / `'Block Trade'`。
    - `page.aStock.blockTrade` 命名空间：title/rank/stockName/stockCode/closePrice/tradePrice/premiumRate/tradeCount/tradeAmount/amountRatio/activeWindow/lastRefresh/sync/dateLabel/datePlaceholder/noData 等键。

16. **`frontend/src/typings/app.d.ts`**（改）：在 `aStock` 下加 `blockTrade: { ... }` 类型块（key 与上一步 i18n 一一对应，全 `string`）。

17. **路由生成**：`cd frontend && pnpm gen-route`（由 elegant-router 自动生成 `a-stock_block-trade` 路由，禁止手改 `src/router/elegant/*`）。

## 业务记忆（1 处，按 AGENTS.MD 要求）

18. **`aiDoc/memory/business/` + 索引**：新增一条业务需求记录「暗盘跟踪模块（大宗交易榜单，源=东方财富/akshare stock_dzjy_*）」，并更新 `memory/project-memory.md` 索引。

## 执行顺序

1. 后端模型 → `__init__.py` 导出 → alembic 迁移（建表+菜单）→ `alembic upgrade head`
2. schema → fetcher → service → endpoint → router 注册 → scheduler task → main.py import
3. 重启后端验证调度任务自动入库（registry → sync_registry_to_db）
4. 前端 typings → api → views → i18n(两份) + app.d.ts → `pnpm gen-route`
5. 用 admin 账号给角色授权 `stock:block_trade:*`，刷新前端验证菜单与页面
6. 写业务记忆 + 更新 aiDoc 索引

## 验证标准

- `uv run alembic upgrade head` 成功，3 张新表 + 菜单行落库。
- 后端启动无报错；调度任务 `stock.block_trade_sync` 出现在 `sys_scheduled_task` 表（is_system=True）。
- `POST /admin/stock/block-trade/sync` 返回 `{fetched, saved}`，数据库有当日快照。
- `GET /admin/stock/block-trade/daily-list` / `active-list` 返回标准化数据。
- 前端「A股 → 暗盘跟踪」菜单可见，页面渲染榜单，日期回看/同步/刷新/自动刷新均正常。
- `cd backend && uv run pytest`（如有 stock 相关测试）+ `cd frontend && pnpm build` 通过。

## 不做的事

- 不纳入逐笔明细（`stock_dzjy_mrmx`）和营业部排行（`yybph`/`hyyybtj`），避免范围蔓延。
- 不改 stock 模块现有代码的行为，仅在 `router.py` / `endpoints/__init__.py` / `business/__init__.py` / `main.py` 做追加式注册。
- 不手写 ORM→dict 转换函数（遵循 backend-layer-rules，用 `model_validate`）。
- 不在 `seed.py` 改任何东西（scheduler 走 registry 自动同步，菜单走 alembic）。