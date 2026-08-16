# A股数据"看似没同步"诊断与修复（资金流 TLS 指纹过滤 + asyncpg 超参数）

## 需求描述

用户反馈「A股数据似乎没有定时同步，请从 akshare 和 baostock 获取最新数据」。诊断结论：**定时任务一直在正常运行**（15:30/15:31/15:35/15:40 均触发成功），数据缺失的真实原因有三个：

1. **东财 push2/push2his 按 TLS 客户端指纹过滤**（本次定位的关键根因）：curl/浏览器指纹正常返回 200，Python httpx/requests（OpenSSL 指纹）被 RemoteDisconnected 断连，且过滤时开时关（观察过同接口 5 分钟内从通到断）。表现为「间歇性限流」。受害者：大盘资金流（akshare `stock_market_fund_flow`，`business_market_fund_flow` 自 8/12 功能上线起 **0 行**）、板块资金流、akshare 指数实时行情。
2. **asyncpg 32767 单语句参数上限**：`BlockTradeService.sync_active` 未分块 upsert，暗盘「近六月」(~1800 行×18 列)、「近一年」(~2800 行) 持续失败。
3. 暗盘每日统计 8/14 当日东财返回 null 缺失一档。

## 状态

已完成

## 涉及范围

### 后端

- `modules/stock/services/market_fetcher.py`
  - `fetch_market_fund_flow` 重构为三级降级链：**httpx 直连（主源，快）→ curl_cffi impersonate=chrome（TLS 指纹保底）→ akshare（接口结构变化时的语义兜底）**
  - 直连东财 `push2his.../fflow/daykline/get`（secid=1.000001 + secid2=0.399001 沪深两市合计，~120 交易日）；klines 字段序：日期,主力,小单,中单,大单,超大单净流入额（校验式：超大单+大单=主力，小单+中单=反向主力）
  - 新增 `FUND_FLOW_RETRY_DELAY` 常量
- `modules/stock/services/board_fetcher.py`：`fetch_board_fund_flow` 加一次退避重试（20s）
- `modules/stock/services/block_trade_service.py`：新增 `_chunked_upsert`（`UPSERT_CHUNK_SIZE=800`），`sync_daily`/`sync_active` 改分块 upsert，修 asyncpg 32767 上限
- `pyproject.toml`：显式声明 `curl_cffi>=0.16.0`（此前仅为传递依赖，随时可能消失）
- 新增 `scripts/sync_astock_latest.py`：一次性手动补拉脚本（复用 Service 层，不启动调度器，幂等）

### 前端

无改动（数据补齐后页面自然恢复）

## 约束与备注

- **东财指纹过滤是运行时态**：httpx 主源在过滤关闭时可用（快），被断连时自动落到 curl_cffi；不要移除任何一级
- 手动补拉要在**交易日收盘后**跑：非交易日跑会把兜底源返回的上一交易日数据打上当天日期戳，产生「伪非交易日快照」（本次 8/16 周日跑过一次，已手动 DELETE 清理 index/board/limit_up 的 8/16 行）
- 板块资金流无需额外兜底：腾讯 getRank 自带净流入字段，`business_board_daily.net_inflow` 无空值
- `sync_daily`/`sync_active` 支持指定日期补数（`target_date` 参数），可直接补历史缺口
- akshare 失败时异常特征：`RemoteDisconnected('Remote end closed connection without response')`；与「IP 封禁」区分方法：curl 同接口能通即为指纹过滤

## 相关文件

- backend/modules/stock/services/market_fetcher.py
- backend/modules/stock/services/board_fetcher.py
- backend/modules/stock/services/block_trade_service.py
- backend/scripts/sync_astock_latest.py
- backend/pyproject.toml

## 记录日期

2026-08-16
