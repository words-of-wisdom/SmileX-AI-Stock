# 暗盘跟踪（大宗交易）模块

## 需求描述

在「A股」目录下新增「暗盘跟踪」子模块，读取东方财富网的大宗交易榜单数据。东方财富没有名为「暗盘」的公开榜单；在 A 股语境中「暗盘」通常非正式指代**大宗交易**（盘后场外撮合，本质 dark pool），其公开数据源即东方财富数据中心「大宗交易」板块（`data.eastmoney.com/dzjy/`），经 akshare 的 `stock_dzjy_*` 系列接口抓取。

模块纳入两个「榜单型」子榜：
- **每日统计**（`stock_dzjy_mrtj`）：按个股聚合的当日大宗交易排行，含成交价/折溢率/成交总额/占流通市值比，主榜单（默认视图）
- **活跃A股统计**（`stock_dzjy_hygtj`）：近一月/三月/六月/一年窗口的大宗交易上榜次数排行

未纳入逐笔明细（`mrmx`，非榜单）与营业部排行（`yybph`/`hyyybtj`，语义偏离个股暗盘）。

## 状态

已完成（2026-08-12 全链路验证通过）

## 验证记录

- `alembic upgrade head` 升至 0013，3 张新表（business_block_trade_daily/active/sync_log）+ 3 条菜单行（MENU + 2 BUTTON，ID 2942406616009011~13）落库
- 后端 6 条路由注册正常（`/admin/stock/block-trade/{sync,sources,daily-list,active-list,dates,history}`）
- 调度任务 `stock.block_trade_sync` 装饰器注册成功（cron `40 15 * * mon-fri`）
- 前端 `pnpm build` 通过，elegant-router 自动生成 `a-stock_block-trade` 路由
- 真实数据 E2E 验证通过：sync_daily(2026-08-12) fetched=37 saved=37；sync_active(近一月) fetched=451 saved=451；get_daily_list/get_active_list/get_sources/get_dates 返回正常

## 涉及范围

### 后端

- **模型**：`database/models/business/block_trade.py` — `BusinessBlockTradeDaily`（每日统计，唯一键 `record_date+stock_code`）、`BusinessBlockTradeActive`（活跃统计，唯一键 `stat_window+stock_code`）、`BusinessBlockTradeSyncLog`（采集日志，`sub_board` 区分 daily/active，`stat_window` 仅 active 有值）
- **模块**：`modules/stock/` 下新增 schemas/services/endpoints
  - endpoints：`block_trade.py` — prefix `/block-trade`，tag「系统管理/暗盘跟踪」
  - services：`block_trade_fetcher.py`（akshare 抓取 + 标准化 dict）、`block_trade_service.py`（upsert 入库 + 排名对比 + 查询）
  - schemas：`block_trade.py` — `BlockTradeDailyItem/ActiveItem/SourceItem/HistoryItem`
- **接口**：`/admin/stock/block-trade/{sync,sources,daily-list,active-list,dates,history}`；权限码 `stock:block_trade:{list,sync,view}`
- **定时任务**：`scheduler/tasks/stock_block_trade_sync.py` — `stock.block_trade_sync`（工作日 15:40 cron，晚于涨停同步 15:35）；main.py 末尾 import 注册
- **迁移**：`alembic/versions/0013_add_block_trade_module.py`（down_revision=0012）— 建 3 表 + 菜单种子（A股目录 ID 9011~9013 段，sort=5）

### 前端

- **页面**：`views/a-stock/block-trade/index.vue` — NTabs 双视图（每日统计 / 活跃A股）；daily 带日期选择器，active 带 4 窗口单选切换；复用 `a-stock/utils.ts`（stockChangeColor/fmtFixed/fmtMoney/isStockAutoRefreshTime）
- **API/类型**：`service/api/block-trade.ts`、`typings/api/block-trade.d.ts`（`Api.BlockTrade` 命名空间）
- **i18n**：`page.aStock.blockTrade.*` + 路由 `a-stock_block-trade`；`App.I18n.Schema` 同步
- **路由**：elegant-router 自动生成 `a-stock_block-trade`

## 约束与备注

- **数据源语义澄清**：「暗盘」=「大宗交易」，非港股新股暗盘（后者东方财富无公开免费接口）。这是 A 股语境下的非正式用法
- akshare 接口字段为中文列名，fetcher 层做中文→英文标准化映射；`成交总额`/`总成交额` 单位为「万元」，直接入库不换算
- **akshare 空响应坑**：`stock_dzjy_mrtj`/`stock_dzjy_hygtj` 内部直接取 `data_json["result"]["data"]`，当东财对无数据日期/限流返回 `result: null` 时抛 TypeError。fetcher 已用 try/except (TypeError, KeyError) 兜底，视为无数据返回空列表（不阻断 sync_all 其它子榜）
- **core insert 绕过 ORM 默认值坑**：用 `insert().values()` + `on_conflict_do_update` 时 `DateTimeMixin` 的 `created_at` 默认值不生效（仅 ORM 构造时触发），rows dict 必须显式带 `created_at: timezone.now()`，否则 NotNullViolationError。`updated_at` 同
- **asyncpg Date 类型坑**：`last_list_date` 列是 Date 类型，asyncpg 不接受字符串（报 `'str' object has no attribute 'toordinal'`）；fetcher 层用 `_to_date()` 统一转 `date` 对象
- 每日统计排名按 `amount_ratio`（占流通市值比）降序；活跃榜排名按 `list_count_total`（上榜总次数）降序；均在内存排序后赋 rank（数据库不存 rank，查询时计算）
- 每日统计含「排名变化」：与上一快照日对比（同 stock_hot 思路）；活跃榜是窗口聚合，无日排名变化
- upsert 用 PG `insert ... on_conflict_do_update`（非 `do_nothing`），同日重抓可更新当日盘中变化
- 活跃榜各窗口数据相对稳定，sync_all 时 4 个窗口都抓一遍；单子榜失败不阻断其它
- 菜单种子 ID 段：0013 用 9011~9013（接 limit-up 的 9010）；新增种子先查库占段
- 权限需给角色授权 `stock:block_trade:list/sync/view` 才能在侧边栏看到菜单
- APScheduler 星期坑：必须用 `mon-fri`，数字 `1-5` 实为周二至周六

## 相关文件

- `backend/database/models/business/block_trade.py`
- `backend/database/models/business/__init__.py`
- `backend/modules/stock/schemas/block_trade.py`
- `backend/modules/stock/services/block_trade_fetcher.py`
- `backend/modules/stock/services/block_trade_service.py`
- `backend/modules/stock/endpoints/block_trade.py`
- `backend/modules/stock/endpoints/__init__.py`
- `backend/modules/stock/router.py`
- `backend/modules/scheduler/tasks/stock_block_trade_sync.py`
- `backend/main.py`
- `backend/alembic/versions/0013_add_block_trade_module.py`
- `frontend/src/views/a-stock/block-trade/index.vue`
- `frontend/src/service/api/block-trade.ts`
- `frontend/src/service/api/index.ts`
- `frontend/src/typings/api/block-trade.d.ts`
- `frontend/src/typings/app.d.ts`
- `frontend/src/locales/langs/zh-cn.ts`
- `frontend/src/locales/langs/en-us.ts`

## 记录日期

2026-08-12
