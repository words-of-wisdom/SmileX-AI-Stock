# 行业板块滚动修复 + 领涨股前三名 + 热门个股连板概率

## 需求描述

三个 a-stock 页面改进（用户要求分步提交）：

1. 行业板块页列表无法滚动（桌面端被裁剪无滚动条）
2. 行业板块领涨股显示前三名，且显示股票代码（原先仅 1 只且东财源无代码）
3. 热门个股页（涨停池）增加连板概率分析

## 状态

已完成

## 涉及范围

### 后端

- `business_board_daily` 新增 `leading_stocks` JSON 列（迁移 0028），存前三名
  `[{code, name, change_pct}]`；旧三字段保留并由 top1 回填
- `board_fetcher`：东财源按板块补抓成分涨幅前三（push2 clist `fs=b:{板块码}&fid=f3&pz=3`），
  域名探测降级链 push2→push2delay（实时源 IP 限流时切延时源，收盘后同步无差异），
  并发 5 + 0.1s 限速；腾讯兜底包装单只（自带代码）、同花顺单只（无代码）、
  单板块失败回退列表自带领涨股
- `limit_up_service.calc_continuation`：连板概率启发式评分 0-100（截断 5..95），
  读时即时计算不入库（历史日期同样可用）；因子：连板高度(20-35)/封成比=封单÷成交额(2-30)/
  炸板次数(0-20)/首封时间(2-20，092500 或 HH:MM:SS 均兼容)/换手率(-6~8)；
  amplitude 库中全空未参与评分
- `LimitUpStockItem` 加 `continuation_probability` + `continuation_factors`（{type, value} 结构化，
  前端 i18n 渲染）

### 前端

- `a-stock/industry-board`：滚动修复（limit-up 页同款 flex-height 模式）；领涨股列渲染前三
  （代码 mono + 名称 + 涨跌标签纵向堆叠），历史数据回退旧单只字段
- `a-stock/limit-up`：连板概率列（NTag ≥65 高/红、40-65 中/橙、<40 低/灰 + NTooltip 因子明细），
  客户端排序
- i18n 三处同步：zh-cn / en-us / app.d.ts（limitUp 段新增 12 key）

## 约束与备注

- 连板概率为**规则启发式评分非模型预测**（用户在规则评分/AI 研判二选一中选了规则评分），
  悬浮提示已注明
- 领涨股前三名用户选择行业+概念都抓（概念约 470+ 板块，手动同步耗时增加约 1 分钟内）
- 概念板块同步走东财源时才有前三名；东财列表源被限流降级腾讯（申万体系）时仅单只领涨股
  （跨源代码体系不同不可混用，见 board_fetcher 头注释）

## 相关文件

- backend/alembic/versions/0028_add_board_leading_stocks.py
- backend/database/models/business/stock_market.py
- backend/modules/stock/services/board_fetcher.py / board_service.py / limit_up_service.py
- backend/modules/stock/schemas/industry_board.py / limit_up.py
- frontend/src/views/a-stock/industry-board/index.vue / limit-up/index.vue
- frontend/src/typings/api/stock-board.d.ts / stock-limit-up.d.ts / app.d.ts
- frontend/src/locales/langs/zh-cn.ts / en-us.ts

## 记录日期

2026-08-31
