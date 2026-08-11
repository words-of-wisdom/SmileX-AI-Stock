# A股行情同步兜底扩展（板块/热榜/指数全覆盖 + 板块入库去重 + 同花顺行业兜底）

## 需求描述

用户反馈「大盘概览、行业板块、股票热榜数据都为空」。排查结论：东财 push2 系列行情接口（clist/ulist）对本机 IP 拒连（RemoteDisconnected），导致板块同步必败（板块表 0 行）、东财人气榜连续失败、指数主源不可用；且 market/board/limit_up 三个收盘后 cron 注册后尚未到首次执行时间。本次为三条链路补齐非东财兜底源，使任一路东财不可用也能出数。

## 状态

已完成（2026-08-11 全链路实测：指数 7/7、热榜 4 源全成功；行业经同花顺兜底 90 条全字段、概念经腾讯兜底 798 条）

## 后续补充（同日第二轮：行业板块成交额/换手率/主力净流入为空）

用户反馈行业板块页的成交额、换手率、主力净流入显示为 `-`。原因：东财被限流时行业落到腾讯兜底，而腾讯板块接口本身无这三个字段。处置：

- **改** `board_fetcher.py`：行业降级链改为 东财 → 同花顺 → 腾讯（概念仍为 东财 → 腾讯，同花顺无概念行情列表）。新增 `_fetch_board_list_ths`：`http://q.10jqka.com.cn/thshy/index/field/199112/order/desc/page/{n}/ajax/1/`，v cookie 由 py_mini_racer 执行 akshare 内置 ths.js 生成；提供成交额/净流入/成交量/涨跌家数/领涨股（无换手率），board_code 取 `ak.stock_board_industry_name_ths()` 名称映射
  - **关键坑**：同花顺表格单元格显示文本带中文单位（"1.88万亿"/"18849.83亿"）且渲染不稳定，pandas read_html 结果因 flavor 而异；必须取 `td[data-value]` 原始值（单位：成交额/净流入=元、成交量=手），按表头 `th[data-field]` 映射列（zdf=板块涨跌幅、10=成交量、199112=成交额、1968584=净流入、104/105=涨跌家数、128=领涨股、zdf2=领涨股涨跌幅）
  - 同花顺与东财行业分类不同（90 个行业 vs 东财 124 个），代码体系为 881xxx，跨源快照不可混用对比
- **改** `board_service.py`：net_inflow 取值在东财资金流映射未命中时回退抓取层自带值（同花顺链有净流入）；同日重同步前先按 (record_date, board_type) 物理删除旧行再插入——降级链换源时板块代码体系不同，仅靠 ON CONFLICT 会残留上一数据源记录造成同日多源混杂
- **换手率缺口**：同花顺行业列表/详情页均无板块级换手率（详情页"换手(%)"是成分股列），腾讯亦无；东财被限流期间换手率仍为 null 显示 `-`，东财恢复后自动有值
- 已实测：今日行业 90 条 turnover/net_inflow 全量有值，与同花顺官网详情页数值逐一吻合；接口 `/admin/stock/board/list` 200 返回完整字段

## 涉及范围

### 后端

- **新建** `modules/stock/services/_sina.py`：新浪 hq.sinajs.cn 批量实时行情辅助层（单次请求批量查，需 Referer 头否则 403；GBK 解码；change_pct/change_amount/amplitude 为计算值）
- **改** `market_fetcher.py`：降级链扩展为 东财 → 新浪实时 → baostock 日线 → 新浪日线；东财/新浪结果必须集齐 7 个追踪指数，否则视为失败继续降级（东财限流时偶发只返回部分分页，会写入残缺快照）
- **改** `board_fetcher.py`：新增同花顺行业兜底（见上方补充）+ 腾讯行情兜底（`proxy.finance.qq.com/ifzqgtimg/appstock/app/mktHs/rank`，行业 t=01 / 概念 t=02，分页 l=100），腾讯提供涨跌幅 + 领涨股；成交额/换手率/涨跌家数无字段置 None；板块资金流东财源优先、同花顺链自带净流入兜底
- **改** `board_service.py`：入库前按 board_code 同批去重——行情实时变动时分页拉取可能跨页重复，同批重复 (record_date, board_type, board_code) 会让 ON CONFLICT DO UPDATE 报 CardinalityViolation 整批失败
- **改** `stock_hot_fetcher.py`：`_fetch_em_rank` 弃用 akshare（其内部依赖 push2 补价格会整体失败），改为自研两步：emappdata 拿排名（sc/rk，无名称）+ 新浪批量行情补名称/最新价/涨跌幅；报价补充失败降级为仅排名

### 前端

无变更（接口契约不变）

## 约束与备注

- 东财 push2 家族（含 1~99.push2 分片、push2his、push2ex 的 clist/ulist）对本机全部拒连，但 emappdata / quote / guba 正常；封禁呈间歇性（盘中偶发放行），故保留东财为主源、兜底源兜间歇失败
- 兜底源数据与主源字段精度有差异：腾讯板块无成交额/资金流，大盘新浪实时快照 record_date 记为当天
- 腾讯板块代码（pt01801154 等）与东财（BK 开头）不同源不同码，跨天历史对比以同一天的快照为准
- 本机同时跑着两个后端实例（8000 与 8123，均带 --reload 与调度器），同一 cron 会被两个进程各执行一次（热榜整点任务日志双倍、sync_log 曾现主键冲突），建议只保留一个跑调度

## 相关文件

- `backend/modules/stock/services/_sina.py`（新建）
- `backend/modules/stock/services/market_fetcher.py`
- `backend/modules/stock/services/board_fetcher.py`
- `backend/modules/stock/services/board_service.py`
- `backend/modules/stock/services/stock_hot_fetcher.py`

## 记录日期

2026-08-11
