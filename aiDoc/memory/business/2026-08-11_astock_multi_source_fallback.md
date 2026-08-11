# A股大盘指数多源降级（akshare + Baostock + 新浪）

## 需求描述

用户要求「使用 akshare + Baostock 作为数据查询回调，查询后需要在本地存储下来」。在现有 A股行情模块基础上，为大盘指数抓取实现多级数据源降级链，并让历史查询在数据不足时自动回补入库，保证查询过的数据沉淀在本地。

## 状态

已完成（2026-08-11 全链路验证通过）

## 验证记录

- 服务层实测：东财 spot 限流时自动降级，sync 抓到 7/7 指数（baostock 6 个 + sina 补齐科创50），record_date 为真实交易日
- 自动回补实测：000001×117 行、000688×118 行（sina）、000905×118 行（em 恢复后）、399006×41 行，UPSERT 幂等重复调用不重复
- HTTP 实测：GET /indices、GET /indices/history 正常，二次调用直接命中 DB
- 浏览器实测：今日 Tab 7 张卡片真实数据、历史 Tab K线图 + 涨跌幅曲线渲染正常

## 涉及范围

### 后端

- **新建** `modules/stock/services/_baostock.py`：baostock 辅助层。`to_bs_code()`（000001→sh.000001 / 399xxx→sz.399xxx）、`_query_index_daily()` 同步查询（login/query/logout 收口单线程）、`fetch_index_daily_bars()` 异步入口（`asyncio.to_thread` 整体包裹）；查询字段 `date,open,high,low,close,preclose,volume,amount,pctChg`，change_amount/amplitude 为计算值
- **改** `market_fetcher.py`：三级降级链
  - spot：东财 `stock_zh_index_spot_em` → baostock 最近日线 bar + sina 补齐缺失指数
  - history：东财 `stock_zh_index_daily_em` → baostock → 新浪（覆盖科创50，无成交额字段，change_pct 差分计算）
- **改** `market_service.py`：`sync_all` 尊重 item 级 `record_date`（兜底数据不错标成今天）；新增 `_backfill_history()`（抓 days×2 自然日 UPSERT 入库）；`get_history` 在行数 `< min(days, 20)` 时自动回补再重读——落实「查询后本地存储」

### 前端

无变更（纯后端数据源层调整，接口契约不变）

## 约束与备注

- **baostock 不覆盖科创50**（sh.000688 查询返回 0 行），故 sina 作为末级兜底专门补齐
- **baostock 日线盘后更新**，盘中取不到当日 bar；sina/东财日线含当日盘中 bar
- 回补触发阈值 `len(rows) < min(days, 20)`：避免「sync 先写 1 行就永远不触发回补」的缺陷
- 板块（行业/概念）与涨停股池仍仅东财源，东财限流恢复前不可用；baostock 兜底时数据为最近交易日日线快照，非实时
- 东财 push2/push2his 有 IP 级临时限流（RemoteDisconnected），sina 目前稳定可用

## 相关文件

- `backend/modules/stock/services/_baostock.py`（新建）
- `backend/modules/stock/services/market_fetcher.py`
- `backend/modules/stock/services/market_service.py`

## 记录日期

2026-08-11
