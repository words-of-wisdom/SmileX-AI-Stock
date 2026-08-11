## 需求描述

增加「资讯」一级目录菜单，将原有「资讯聚合」降为其子菜单，并新增「股票热榜」菜单。股票热榜读取东方财富、雪球、同花顺三源热榜数据，支持每日排名变化跟踪。

## 状态

已完成

## 涉及范围

### 后端

- **模型**：`database/models/business/stock_hot.py` — `BusinessStockHotRank`（快照表，联合唯一 `record_date+source+stock_code`）+ `BusinessStockHotSyncLog`（采集日志）
- **抓取层**：`modules/admin/services/sys/stock_hot_fetcher.py` — 东财 `stock_hot_rank_em`、雪球 `stock_hot_follow_xq`/`stock_hot_tweet_xq`（akshare）、同花顺自研 httpx 抓取
- **服务层**：`modules/admin/services/sys/stock_hot_service.py` — 抓取入库（`ON CONFLICT DO NOTHING`）+ 排名对比（`prev_rank - cur_rank`）
- **接口**：`modules/admin/endpoints/sys/stock_hot.py` — `/admin/sys/stock-hot/{sources,list,dates,history}`，权限码 `sys:stock_hot:{list,view,sync}`
- **定时任务**：`modules/scheduler/tasks/stock_hot_sync.py` — 每小时抓取
- **迁移**：`alembic/versions/0006_stock_hot.py` — 建表 + 菜单重组（新增 `info` 目录、降级 `news` 为子菜单、新增 `stock-hot`）

### 前端

- **页面**：`frontend/src/views/stock-hot/index.vue` + `modules/stock-hot-source-tabs.vue`
- **API**：`frontend/src/service/api/stock-hot.ts`
- **类型**：`frontend/src/typings/api/stock-hot.d.ts`
- **i18n**：zh-cn.ts / en-us.ts 路由 `info_news`/`info_stock-hot`/`info`，页面 `stockHot.*`
- **elegant-router**：routes.ts / imports.ts / transform.ts / elegant-router.d.ts 同步更新

## 约束与备注

- akshare 无同花顺热榜函数，自研 httpx 抓取 `data.10jqka.com.cn`，失败降级不影响其他源
- 排名变化口径：同一 source 内对比相邻两个不同 `record_date` 的快照
- 菜单 `name` 遵循 elegant-router 命名约定：目录 `info`，子菜单 `info_news`/`info_stock-hot`
- 权限码用后端 snake_case：`sys:stock_hot:*`

## 相关文件

- `backend/database/models/business/stock_hot.py`
- `backend/modules/admin/services/sys/stock_hot_fetcher.py`
- `backend/modules/admin/services/sys/stock_hot_service.py`
- `backend/modules/admin/endpoints/sys/stock_hot.py`
- `backend/modules/admin/schemas/sys/stock_hot.py`
- `backend/modules/scheduler/tasks/stock_hot_sync.py`
- `backend/alembic/versions/0006_stock_hot.py`
- `frontend/src/views/stock-hot/index.vue`
- `frontend/src/service/api/stock-hot.ts`
- `frontend/src/typings/api/stock-hot.d.ts`

## 记录日期

2026-08-10
