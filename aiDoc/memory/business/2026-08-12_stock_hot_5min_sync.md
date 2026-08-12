# 股票热榜开盘时段每 5 分钟同步

## 需求描述

股票热榜（东财/雪球/同花顺几个榜单）需要在开盘时间里每 5 分钟同步一次，取代原来的每小时一次全时段抓取。

## 状态

已完成

## 涉及范围

### 后端

- `modules/scheduler/tasks/stock_hot_sync.py`：cron `0 * * * *` → `*/5 9-15 * * mon-fri`，任务内新增 `_in_trading_hours` 守卫（周一至周五 09:30-11:30、13:00-15:00 连续竞价时段，非时段直接跳过返回 `{"skipped": True}`）
- `modules/scheduler/tasks/stock_market_sync.py`：三个收盘任务 cron 星期字段 `1-5` → `mon-fri`（顺带修 bug）

### 前端

无

## 约束与备注

- 单条 cron 无法表达跨小时的分钟边界（9:30-11:30、13:00-15:00），故 cron 放宽到 9-15 点每 5 分钟触发，任务内按交易时段守卫跳过；守卫同时兜住自然周末
- **APScheduler 星期坑**：`CronTrigger` 的星期字段 Monday=0，数字 `1-5` 实为周二至周六（周六会触发、周一被跳过）。原三个收盘行情任务（大盘/板块/涨停池 `30/31/35 15 * * 1-5`）因此漏掉周一收盘数据，本次一并改为 `mon-fri`。后续新任务禁止用数字星期
- 法定节假日休市判断未做（需要交易日历数据源），节假日会照常触发抓取，源站返回的多为前一交易日数据，靠 `(record_date, source, stock_code)` 联合唯一约束去重，影响可控
- 同日多次抓取仍只保留当日首次快照（on_conflict_do_nothing），盘中排名/价格变动不会覆盖既有行，只会补进新上榜个股；如需盘中快照明细需另建历史表
- 装饰器 cron 变更经 `sync_registry_to_db` 在启动时同步入库，重启后生效

## 相关文件

- `backend/modules/scheduler/tasks/stock_hot_sync.py`
- `backend/modules/scheduler/tasks/stock_market_sync.py`
- `backend/modules/stock/services/stock_hot_service.py`（抓取入库逻辑，未改）

## 记录日期

2026-08-12
