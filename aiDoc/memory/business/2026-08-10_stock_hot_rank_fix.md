# 股票热榜跳转与雪球/同花顺加载修复

## 需求描述

股票热榜页面存在三类问题：
1. 点击股票名跳转雪球行情页失效（部分股票跳到 404）
2. 雪球（关注/讨论榜）榜单数据异常
3. 同花顺榜单完全无法加载

## 状态

已完成

## 根因与修复

### 雪球代码带交易所前缀导致跳转失败（跨栈契约）

akshare 的 `stock_hot_follow_xq` / `stock_hot_tweet_xq` 返回的"股票代码"带交易所前缀（如 `SH600519`），而 fetcher 原样入库；前端 `openStockPage` 又按代码首位拼前缀（`6→SH`，其余→`SZ`），对 `SH600519` 这种值会拼出 `SZSH600519`，雪球返回 404。

修复（契约统一为**纯数字代码**）：
- **后端**：`stock_hot_fetcher.py` 新增 `_normalize_code()`，在 `_item()` 内统一剥离 `SH/SZ/BJ`（含 `.SH` 后缀）前缀，所有源入库均为纯数字
- **前端**：`openStockPage` 先剥离可能的历史前缀（兼容旧数据），再按首位判交易所：`6→SH`、`8/4→BJ`（北交所）、其余→`SZ`

### 雪球全量返回未截断

akshare 雪球接口返回的是全量股票（5000+），fetcher 全量入库，前端表格渲染卡顿。修复：截断为热榜 Top 100。

### 同花顺接口拿错 + 正则解析 JS 渲染页必然失败

原 `_fetch_ths_hot` 请求的是龙虎榜页面 `data.10jqka.com.cn/market/longhu/`（且 JS 渲染，正则无法解析），每次同步必抛异常。akshare 无同花顺热榜接口。

修复：改用同花顺"富贵" hot_list JSON 接口 `dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock`，参数 `stock_type=a&type=day&list_type=normal&page_size=100`，解析 `stock_list`（`code`/`name`/`order`/`rate`/`rise_and_fall`）。

### 过渡期脏数据清理

历史雪球数据存成了带前缀代码，与修复后的纯数字记录同日并存会导致列表重复。`sync_all` 入库前先清理当天该源 `stock_code` 以 `SH/SZ/BJ` 开头的旧记录。

## 涉及范围

### 后端

- `backend/modules/admin/services/sys/stock_hot_fetcher.py` — `_normalize_code`、雪球 Top100 截断、同花顺接口重写
- `backend/modules/admin/services/sys/stock_hot_service.py` — `sync_all` 入库前清理当天带前缀脏数据（新增 `delete`/`or_` import）

### 前端

- `frontend/src/views/info/stock-hot/index.vue` — `openStockPage` 剥离前缀 + 北交所(BJ)支持

## 约束与备注

- **跨栈契约**：`stock_code` 统一为**纯数字**（6 位），前后端均不应再处理带前缀值
- 同花顺 `rise_and_fall` 为百分点数值（4.21 = +4.21%），与东财 `change_pct` 口径一致
- 排名变化对比依赖 stock_code 一致；代码规范化后，首个过渡日的历史排名对比会全部显示为 NEW（次日恢复正常）

## 相关文件

- `backend/modules/admin/services/sys/stock_hot_fetcher.py`
- `backend/modules/admin/services/sys/stock_hot_service.py`
- `frontend/src/views/info/stock-hot/index.vue`

## 记录日期

2026-08-10
