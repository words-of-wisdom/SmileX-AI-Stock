# 动态止盈：回撤止盈 + AI 复核兜底

## 需求描述

市场冲高回落时，价格未触及固定的 `target_sell_price` 就跌回来，浮盈回吐甚至转亏，系统无任何动作。需要"未到目标价但市场已变化也止盈"的机制。

方案（用户选定）：**程序化回撤止盈为主 + AI 复核兜底**，回撤参数策略级可配置。

## 状态

已完成（2026-08-29）

## 机制

1. **回撤止盈（机械规则）**：持仓每 tick 滚动刷新 `peak_price`（持仓期间最高价）；当 `现价 <= peak × (1 - trailing_drawdown_pct/100)` 且仍浮盈（现价 > 买价，跌破买价交由止损线）→ 平仓，`sell_reason = "trailing_stop"`。T+1 当日买入不触发。
2. **AI 预警复核兜底**：回撤达阈值一半（预警线）但未触发机械止盈时，写 TrackLog（adjust_reason 记峰值/回撤明细）并把策略加入 `review_strategy_ids`，复用涨停复核链路（`_submit_limit_reviews`，30 分钟节流 + running 并发守卫），AI 可提前 sell / adjust 上移止损 / hold。
3. 参数**建仓时快照**到持仓行（`position.trailing_drawdown_pct`），与 target/stop_loss 一致，策略后续改参不影响存量持仓。

## 涉及范围

### 后端（迁移 0025 + modules/strategy/）
- `business_ai_strategy` 加 `trailing_drawdown_pct`（默认 5.0）；`business_strategy_position` 加 `trailing_drawdown_pct`（快照）+ `peak_price`（存量 holding 用 GREATEST(buy_price, latest_price) 回填、快照继承策略值）。
- `position_service.track_positions`：峰值刷新 + 回撤止盈/预警复核分支（排在止损/涨停保护之后）。
- `trade_engine`：建仓时初始化快照与 `peak_price=price`。
- `strategy_executor`：复核提示词扩为"涨停保护或浮盈回撤预警触发"；持仓行注入峰值与距峰值回撤幅度、回撤止盈线。
- schemas：`StrategyCreateRequest/StrategyItem` 加 `trailing_drawdown_pct`；`PositionItem` 加 `trailing_drawdown_pct/peak_price`；service create/update 透传（`or None` 使 0=不启用）。

### 前端（views/ai/analysis/）
- 策略编辑抽屉加"回撤止盈(%)"数字输入（默认 5）；`strategy.d.ts` 同步字段。
- 持仓 `sell_reason` 文案映射加 `trailing_stop → 回撤止盈`；i18n zh-cn/en-us 加 `reasonTrailingStop/trailingDrawdown`。
