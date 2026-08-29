# 动态止盈：回撤止盈（trailing stop）+ AI 复核兜底

## 背景
当前止盈只在现价 ≥ 固定 `target_sell_price` 时触发（`position_service.py:105`）。市场冲高回落时，价格从未触及目标价就跌回来，浮盈回吐甚至转亏，系统无任何动作。

## 机制设计
1. **程序化回撤止盈（主规则）**：持仓期间每 tick 记录最高价 `peak_price`；当 `现价 <= peak_price × (1 - trailing_drawdown_pct/100)` 且仍处浮盈（现价 > 买价，跌破买价交由止损线处理）→ 机械卖出，`sell_reason = "trailing_stop"`。
2. **AI 复核兜底（预警线）**：回撤幅度达到阈值的一半（预警线）但尚未触发机械卖出时，把该策略加入 `review_strategy_ids`，复用现有涨停复核链路（`_submit_limit_reviews`，30 分钟节流 + running 并发守卫）提交 AI 盘中复核，AI 可提前 sell / adjust 上移卖点 / hold。
3. T+1 约束沿用：当日买入不触发回撤卖出（与现有止损止盈一致）。

## 改动清单

### 1. 数据模型 + Alembic 迁移
- `database/models/business/strategy.py`：
  - `BusinessStrategyPosition` 加 `peak_price: Mapped[Optional[Numeric]]`（持仓期间最高价，建仓时初始化为买价）
  - `BusinessAiStrategy` 加 `trailing_drawdown_pct: Mapped[Optional[Numeric]]`（回撤止盈百分比）
- 新迁移（基于当前 head）：
  - 两表加列，`trailing_drawdown_pct` server_default `'5.0'`（存量策略默认启用 5% 回撤止盈）
  - 存量 holding 持仓的 `peak_price` 用 `GREATEST(buy_price, latest_price)` 回填初始化
  - 注意 alembic bulk 操作已知坑（memory：首行键编译列丢值等），用标准 add_column + update

### 2. 持仓跟踪 `position_service.py::track_positions`
- 方法新增 `strategies: dict[int, BusinessAiStrategy]` 参数（或内部查询），取 `trailing_drawdown_pct`
- 每 tick：`pos.peak_price = max(pos.peak_price or price, price)`
- 触发链（T+1 判定内，排在止损/止盈之后）：
  ```
  elif drawdown_pct 存在 and peak 有效:
      回撤 = (peak - price) / peak * 100
      if 回撤 >= drawdown_pct and price > buy_price:
          sell_reason = "trailing_stop"
      elif 回撤 >= drawdown_pct / 2:
          review_strategy_ids.add(pos.strategy_id)  # AI 预警复核兜底
          写 TrackLog(adjust_reason=f"冲高回落{回撤:.1f}%接近回撤止盈线，AI复核")
  ```
- 建仓处（`trade_engine.py:248`）同步初始化 `peak_price=price`

### 3. trade_engine.py
- 拉取策略后传入 `track_positions`（策略已在 step 4 查出，复用即可）
- `_submit_limit_reviews` 复用不改逻辑（来源策略集合同时含涨停保护与回撤预警）

### 4. strategy_executor.py 复核 prompt 微调
- `_build_user_prompt(is_review=True)` 文案从"涨停保护触发的盘中持仓复核"扩为"涨停保护/浮盈回撤预警触发的盘中持仓复核"，并注入当前 `peak_price`/回撤幅度，让 AI 有判断依据

### 5. Schemas / Endpoint / 前端
- `modules/strategy/schemas/strategy.py`：`StrategyItem`/创建/更新 schema 加 `trailing_drawdown_pct`；`PositionItem` 加 `peak_price`；Swagger 注释同步
- 前端策略编辑表单（`frontend/src/views/strategy/`）加"回撤止盈(%)"数字输入，默认 5
- 前端持仓列表 `sell_reason` 文案映射加 `trailing_stop → 回撤止盈`
- 同步更新 `aiDoc/frontend-backend/` 契约说明

### 6. 文档与记忆
- 按仓库规则新增 `aiDoc/memory/business/` 一条业务需求记忆并更新需求索引

## 验证
- 用实际库（smilex_ai_stock，验证脚本先 `init_pool()`）跑迁移 upgrade
- 单测/手工脚本验证 track_positions：模拟 peak 回撤超阈值→平仓、半阈值→进 review 集合、跌破买价→走止损而非回撤止盈、T+1 不触发