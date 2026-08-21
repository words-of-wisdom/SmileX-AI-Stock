# 股票热榜滚动更新 + 数据补全

## 需求描述

用户反馈：股票热榜的数据没有定时刷新，同时数据不完整。

## 状态

已完成

## 根因诊断

1. **"没有定时刷新"**：定时任务本身一直在跑（当日日志 `last_status=success`），但入库用 `on_conflict_do_nothing`——联合唯一键 `(record_date, source, stock_code)` 使当日首次同步后，后续每 5 分钟的同步 `saved_count≈0`（全部冲突被忽略），排名/价格永不更新、掉榜股票不移除（榜单累积到 117~153 行），页面数据停在当天第一次抓取时点。
2. **"数据不完整"**（各源整列恒空，查库证实）：
   - `xq_follow`/`xq_tweet`：涨跌幅恒空——akshare `stock_hot_xq.py` 只返回 股票代码/股票简称/关注/最新价 4 列（已查证上游源码）
   - `ths_hot`：最新价恒空——同花顺富贵 hot_list 接口无该字段
   - `em_rank`：热度值恒空——实测 emappdata `getAllCurrentList` 每项仅 `sc/rk/rc/hisRc`，无热度字段

## 涉及范围

### 后端

- `modules/stock/services/stock_hot_service.py`：
  - `sync_all` 改滚动更新：`on_conflict_do_nothing` → `on_conflict_do_update`（覆盖 rank/stock_name/latest_price/change_pct/hot_value/updated_at，沿用项目 `stmt.excluded` 惯例）
  - 新增掉榜清理：upsert 后删除当日该源 `stock_code NOT IN (本次抓取代码集)` 的行，榜单始终为最新 Top N
  - 「排名变化」语义不变：仍对比上一交易日快照（查询层未动）
- `modules/stock/services/stock_hot_fetcher.py`：
  - 新增 `_fill_quotes(client, items)` 统一行情补全：对 latest_price/change_pct/名称缺失的项，按首位映射新浪前缀（6→sh、4/8→bj、其余→sz，与前端 openStockPage 口径一致）批量调 `fetch_spot_quotes`，**只填空缺不覆盖源站原值**，失败仅告警
  - `_fetch_xq`/`_fetch_ths_hot` 接入补全（雪球补涨跌幅、同花顺补最新价）
  - `_fetch_em_rank` 重构复用补全（占位名称=纯数字代码，`_fill_quotes` 识别 name==code 后替换为新浪名称），热度填 `101 - rank` 合成指数（非源站原始数据，代码注释已标明）
  - 新增 `_to_sina_code` 纯数字代码→新浪代码映射
- `modules/scheduler/tasks/stock_hot_sync.py`：下午交易窗守卫 15:00 → 15:05，收盘后最后一轮（cron `*/5 9-15` 在 15:05 触发）抓到定型收盘数据
- `modules/agent/tools/stock_tools.py`：`get_hot_stocks` 的 source 参数描述改为真实 key（em_rank/xq_follow/xq_tweet/ths_hot），原描述 eastmoney/10jqka/xueqiu 传错即报"来源不存在"

### 前端

无（列渲染已兼容 null，补全后自然显示）

## 约束与备注

- 每天每股每源仍只一行，当日快照始终是最新时点；如需盘中快照明细回放须另建历史表（本次不做）
- 东财热度是合成指数（101-排名），跨源语义不同（雪球=关注数、同花顺=rate），前端按源内 maxHot 归一化展示故视觉一致
- akshare 雪球接口无涨跌幅列是上游事实，新浪批量行情一次请求可补全 100 码
- 北交所代码新浪 hq 是否覆盖未验证，拿不到报价时该股字段保持空（不影响其他行）
- xq_tweet 验证时有 1/100 涨跌幅未补上（疑似停牌无新浪报价），属预期降级

## 验证结果（2026-08-20 盘后实测）

- 连续两次 `sync_all`：均 `saved=400`（4 源全量滚动更新），第二次 `updated_at` 100/100 刷新
- 字段完整度：em_rank 热度 100/100（rank1→100 分递减）、ths_hot 最新价 100/100、雪球涨跌幅 99~100/100
- 掉榜清理：各源从累积 117~153 行收敛为精确 100 行；sync_log `saved_count` 稳定 100

## 相关文件

- `backend/modules/stock/services/stock_hot_service.py`
- `backend/modules/stock/services/stock_hot_fetcher.py`
- `backend/modules/stock/services/_sina.py`（复用，未改）
- `backend/modules/scheduler/tasks/stock_hot_sync.py`
- `backend/modules/agent/tools/stock_tools.py`

## 记录日期

2026-08-20
