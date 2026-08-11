# A股行情模块

## 需求描述

新增「A股」一级目录，包含大盘概览（今日/历史大盘双 Tab）、行业板块（行业/概念 + 时间范围 + 涨跌幅/资金流排序）、热门个股（涨停股池 + 主板/创业板/科创板筛选）三个子页面，并将原「股票热榜」从资讯目录迁移到 A 股下。数据源统一 akshare，采用「定时同步入库 + 手动触发同步」模式（同股票热榜）。一期以逻辑结构搭建为主。

## 状态

已完成（2026-08-10 全链路验证通过）

## 验证记录

- 后端 18 条路由注册正常，alembic 已升到 0011（含他人 0010/0011 共存处理）
- 浏览器端到端验证通过（admin 登录）：
  - 大盘概览：今日 Tab 7 张指数卡片红涨绿跌正常；历史 Tab ECharts K 线图正常渲染
  - 行业板块：行业/概念切换、排序单选、日期选择、表格渲染正常（成交额列显示 "-"，东财板块列表接口无成交额字段，刻意置空不错用总市值）
  - 热门个股：真实数据 99 家涨停渲染正常（主板94/创业板4/科创板1，最高5连板；板块筛选精确）
  - 股票热榜（迁移后）：4 源 Tab + 表格正常
- 前端 typecheck 仅剩 6 个基线存量错误（uno-preset/news/file 相关，与本模块无关）
- 验证用演示数据（market_index 70 条 + board 20 条）已清理；limit_up 99 条为真实数据已保留

## 涉及范围

### 后端

- **模型**：`database/models/business/stock_market.py` — `BusinessMarketIndexDaily`（指数日快照）、`BusinessBoardDaily`（行业/概念统一表）、`BusinessLimitUpStock`（涨停股池），均联合唯一 `record_date + 代码`，UPSERT 幂等
- **模块**：`modules/stock/`（独立模块，router 前缀 `/admin/stock`）— endpoints(market_overview/industry_board/limit_up/stock_hot) + services(fetcher/service 双层) + schemas
- **接口**：`/admin/stock/market/{indices,indices/history,dates,sync}`、`/admin/stock/board/{list,history,dates,sync}`、`/admin/stock/limit-up/{list,stats,dates,sync}`、`/admin/stock/stock-hot/*`（迁移，契约不变）；权限码 `stock:{market,board,limit_up}:{list,sync}`
- **定时任务**：`scheduler/tasks/stock_market_sync.py` — 收盘后 `stock.market_sync`/`stock.board_sync`/`stock.limit_up_sync`（15:30/15:31/15:35 工作日 cron）；stock_hot_sync 迁移并保持每小时
- **迁移**：`alembic/versions/0010_add_stock_market_module.py` — 建 3 张表 + 菜单重组（A股目录 2942406616009001 段，股票热榜挪入）；0011 是他人 demo_stock-sdk 菜单，ID 冲突时改 2942406616010001
- **错误码**：11101-11104（`CustomErrorCode` + i18n yaml）

### 前端

- **页面**：`views/a-stock/{market-overview,industry-board,limit-up,stock-hot}/`；market-overview 内 NTabs 双 Tab（today-market 指数卡片网格 / history-market 指数选择器 + ECharts）
- **API/类型**：`service/api/stock-market.ts`、`stock-board.ts`、`stock-limit-up.ts`，`typings/api/stock-*.d.ts`（`Api.StockMarket/StockBoard/StockLimitUp` 命名空间）；stock-hot.ts URL 前缀改 `/admin/stock/stock-hot/`
- **i18n**：`page.aStock.*` + 路由 `a-stock*` key；`App.I18n.Schema` 同步
- **路由**：elegant-router 自动生成 4 条 `a-stock_*` 视图路由

## 约束与备注

- akshare 覆盖全部需求，无需券商 MCP：`stock_zh_index_spot_em`（指数）、`stock_zh_index_daily_em`（历史）、`stock_board_industry/concept_name_em`（板块）、`stock_sector_fund_flow_rank`（资金流）、`stock_zt_pool_em`（涨停池）
- 涨停股 market_board 按代码前缀推导：60/00→main、30→chinext、688→star、8/4→bse
- `limit_up_reason` 预留 nullable 字段，akshare 不直接提供时兜底 null
- 振幅 amplitude 若接口不返回则从 high/low/prev_close 计算
- **东财 push2 接口对短时间高频请求会 IP 级临时限流**（RemoteDisconnected，约数分钟至更久恢复）；fetcher 抓取注意串行 + 间隔，生产 cron 已错开分钟。2026-08-10 调试期间触发限流导致当晚大盘/板块手动 sync 不可用，次日 cron 低频调用不受影响自动补齐
- 字段可空性：板块成交额、涨停原因 limit_up_reason、振幅 amplitude 在 akshare 对应接口不直接提供时按方案预留 null（页面显示 "-"）
- 菜单种子 ID 段位约定：0006 用 600x、0009 用 800x、0010 用 900x、0011 用 1000x，新增种子先查库占段
- NDatePicker 值用时间戳 + dayjs 格式化（项目惯例）；TSX 中 NaiveUI props 不写 `:bordered` JSX 简写

## 相关文件

- `backend/database/models/business/stock_market.py`
- `backend/modules/stock/`（router.py、endpoints/、services/、schemas/）
- `backend/modules/scheduler/tasks/stock_market_sync.py`
- `backend/alembic/versions/0010_add_stock_market_module.py`
- `frontend/src/views/a-stock/`
- `frontend/src/service/api/stock-market.ts`、`stock-board.ts`、`stock-limit-up.ts`
- `frontend/src/typings/api/stock-market.d.ts`、`stock-board.d.ts`、`stock-limit-up.d.ts`

## 记录日期

2026-08-10
