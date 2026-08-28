# 持仓跟踪页筛选/排序/滚动改造 + 亏损归因分析

## 需求描述

1. AI 分析-持仓跟踪 Tab：列表过长无法滚动（内容被裁剪）；增加策略筛选、时间段（建仓时间）筛选、盈亏排序。
2. 分析模拟盘亏损根因：是股票数据未及时同步，还是策略问题。

## 状态

已完成（2026-08-28）

## 涉及范围

### 后端（`modules/strategy/`）
- `GET /admin/strategy/positions` 新增 query 参数：`start_time`/`end_time`（ISO 8601，按 `buy_time` 过滤，非法串静默忽略，naive 视为本地时区）、`sort_by`（buy_time/sell_time/pnl/return_rate 白名单，pnl→floating_pnl_pct）、`sort_desc`。
- `PositionService.get_positions`：指定 sort_by 时按该列排序（`nulls_last`），holding 前置 + buy_time desc 仍为默认排序。

### 前端（`views/ai/analysis/index.vue`）
- 滚动修复：持仓 Tab 内容包一层 `h-full flex-col-stretch`，NDataTable 加 `:flex-height="!appStore.isMobile"` + `remote` + `class="flex-1-hidden"`（对齐 openapi-log 等可滚动表格页模式），分页条保持在表格下方。
- 筛选：策略 NSelect（filterable/clearable，独立全量加载选项 page_size=100，不受策略 Tab 搜索影响）+ NDatePicker datetimerange（dayjs 格式化为 `YYYY-MM-DDTHH:mm:ss` 传后端）。
- 排序：buy_time/sell_time/浮盈/收益率列加 `sorter: true`，`@update:sorter` 映射列 key→后端 sort_by（floating_pnl_pct→pnl），服务端排序（remote 模式，非本地排序）。
- i18n：filterStrategy/filterTimeRange（zh-cn/en-us/app.d.ts Schema 三处同步）。

## 亏损归因结论（代码层）

1. **执行价格不是问题**：trade_engine 每分钟 tick 直接调新浪实时行情（quote_helper，无缓存无 DB 中间层），延迟 ≤1 分钟。
2. **信号生成侧数据时效错位**：AI 分析工具（get_market_indices/get_board_ranking/get_limit_up_stocks）读每日 15:30-15:40 收盘后同步的 DB 快照，盘中策略看到的是**昨日**大盘/板块/涨停数据（仅热榜 5 分钟级新鲜）——AI 基于过期市场环境选股是嫌疑主因。
3. **T+1 结构性风控缺口**：当日买入持仓止损/止盈均不触发（position_service.track_positions 的 is_t1_locked 分支），买入当日暴跌无法止损。
4. 数据验证（SQL）结论见下文补充。

## SQL 数据验证（2026-08-28，库 smilex_ai_stock）

- 已平仓 32 笔，平均 -1.89%/笔；其中 **stop_loss 20 笔（62.5%）平均 -5.37%**，target_reached 7 笔 +5.89%，ai_signal 5 笔 +1.14% → 期望收益为负。
- **信号参考价与实际成交价偏差巨大**：67 笔已执行买入信号，|ref_buy_price - executed_price|/ref 平均 **29.3%**，15 笔 >5%，最大 953%（601869 ref 40.5 实成交 426.8；002463 ref 55 实 123；000988 ref 45 实 106）→ AI 拿不到实时价，参考价过期/幻觉，买入远高于其假设价位。
- 当日买当日平仅 1 笔；止损单集中在买入后 1-2 天（bucket1 平均 -4.27%、bucket2 -6.26%）→ T+1 缺口目前影响有限，非主因。
- 近 7 天定时任务 49003 success / 71 timeout（全是 news.sync_all，不影响行情）→ **数据同步任务本身没有失败**。
- 结论：执行侧数据链路健康（引擎实时价 + 同步任务全成功）；**根因在策略生成侧**——信号基于昨日快照且参考价严重失真 + 止损触发率过高（62.5%）期望为负。改进方向：信号生成注入实时行情、参考价超阈值拒单/重算。

## 2026-08-28 追加：实时行情注入 + 参考价偏差拒单

基于上述归因落地两项改进（`modules/strategy/`）：
- **strategy_executor**：`_analyze` 在 LLM 分析前拉取候选股（股票池 ∪ 持仓股）新浪实时价（`fetch_latest_prices`，失败降级空 dict）；`_build_user_prompt` 新增 `realtime_quotes` 参数，注入「实时行情快照」章节并声明 buy_price 必须以此为准、快照缺失的股禁止 buy、快照整体失败时禁止任何 buy 信号；系统提示词工作流程补 3~5 条价格纪律（buy_price 锚定实时价 ±2%、止损/目标方向与风控比例、明显追高宁可不买）。
- **trade_engine**：买入执行前参考价守卫 `REF_PRICE_MAX_DEVIATION_PCT = 3.0`——实时价与 `ref_buy_price` 偏差超 3% 时 `skipped` 拒单（result_msg 记录偏差明细），防 AI 过期/幻觉价位下的建仓。sell/adjust 不受影响。
- 注意：拒单后信号不再重试（status=skipped 终态），依赖下一轮分析（每 10 分钟）重新生成信号。

## 2026-08-28 二次追加：基于归因数据调整 10 条预置策略

按策略维度复盘（32 笔平仓）：**尾盘趋势确认 5/5 全止损（-29.83%）、尾盘资金抢筹 3/3 全止损（-20.95%）、午盘强势回踩低吸 6/8 止损（-13.32%）**；唯一盈利=涨停题材龙头打板（+7.28%）。另一关键发现：**实际止损亏损是配置止损位的 1.5~2.8 倍**（尾盘资金抢筹配 2.5% 实亏 6.98%）——止损均为隔夜跳空/分钟级滞后穿越造成，非止损位设置过窄。

调整（改 `0016` 种子定义 + 同一份定义回写运行库 5 条，保证零漂移）：
- **尾盘资金抢筹**：max_positions 3→2、止盈 8→6；纪律加「只选全天涨幅 2%~5% 温和放量；当日涨幅>6% 或尾盘直线拉升一律不买（历史亏损集中于此）」
- **尾盘趋势确认**：max_positions 5→3、止盈 10→7；纪律加「回避当日涨幅>7%、连续拉升 3 日以上加速股」
- **午盘强势回踩低吸**：止盈 6→5；纪律加「必须回踩至分时均价线附近企稳才 buy，禁止高位追多；涨幅>6% 不买」
- **竞价高开抢筹**：止盈 5→4；纪律加「高开>6% 一律不追；竞价须量比>2 且非巨量出逃」
- **午盘补涨轮动**：止盈 10→7
- 不动：涨停题材龙头打板（唯一盈利）、两条蓝筹、大盘共振波段、竞价超跌低吸（样本少）
- 已应用的 0016 迁移被编辑（项目惯例：预置策略种子以 0016 为真源，新环境一致；存量库用脚本按 name+is_preset 回写）

## 2026-08-28 三次追加：新增预置策略「资金潜伏低吸」（seq 11）

- 逻辑：板块资金**连续 ≥3 日净流入且放大**但阶段涨幅平庸（资金吸筹未兑现）→ 板块内选近 10 日无 7%+ 单日涨幅、无涨停、无 10%+ 阶段大涨的温和放量个股潜伏，等资金发酵主升。
- 配置：category=general，execute_periods=["noon","tail"]，max_positions=4，止损 4%，止盈 10%；纪律：买点须近平台/支撑、当日涨幅>5% 不买、3~5 日资金转流出且滞涨主动换股、宁缺毋滥。
- 落地：0016 `_PRESET_STRATEGIES` 加 seq 11（新环境真源）+ 直接 INSERT 运行库 id=2942406616009111（**status=true 直接启用**，区别于其他预置默认停用）；坑：`execute_periods` 列是 `json` 不是 `jsonb`，参数 cast `::jsonb` 会报错。

## 2026-08-28 四次追加：涨停暂缓平仓（连板潜力二次研判）

问题：`track_positions` 的 target_reached 是机械平仓——涨停封板瞬间达到目标价就自动卖出，砍掉连板溢价。改为**涨停保护**：
- `quote_helper` 新增 `fetch_latest_quotes`（{code: {price, change_pct}}），`fetch_latest_prices` 变薄包装；`_sina` 本就解析 change_pct（f[2]昨收/f[3]最新）。
- `position_service.track_positions`：目标价触发但当日涨跌幅 ≥ 涨停阈值（`limit_up_threshold`：30/68 开头 19%、4/8 北交所 29%、主板 9%）→ 不平仓，写 TrackLog（adjust_reason 记"涨停暂缓平仓，等待AI二次研判"），交由每 10 分钟策略分析对持仓二次研判（hold/adjust 上移卖点/sell）；若开板回落价格仍 ≥ 目标则下一分钟正常平仓。止损不受影响。
- `trade_engine`：一次拉 quotes 派生 prices/changes 透传；返回统计加 `limit_protected`。
- AI 卖出侧：SYSTEM_PROMPT 加纪律「封死涨停的持仓不给 sell（连板潜力保留），高位炸板/放量滞涨/尾盘跳水果断 sell」；`_build_user_prompt` 持仓行注入现价相对买价涨幅，供二次研判。

## 2026-08-28 五次追加：涨停保护触发 AI 即时复核（补时段空窗）

问题：`strategy.run_execute` 是**同日同时段去重**（每时段只跑一次），早盘封板要等 13:00 才有下一次 AI 研判，空窗最长 3 小时。改为**持仓触发的即时复核**：
- `track_positions` 返回新增 `review_strategy_ids`（发生涨停保护的策略集合）。
- `trade_engine._submit_limit_reviews`：tick 末尾为这些策略直接 `submit_run(run_period="review", trigger_type="review")`——不受时段窗口限制、不限 execute_periods；**30 分钟节流**（`REVIEW_THROTTLE_MINUTES`，按 review run 的 created_at 查重）+ submit_run 并发守卫兜底；提交失败不阻断 tick。
- `EXECUTE_PERIOD_NAMES` 加 `"review": "盘中持仓复核（涨停保护触发）"`；`_build_user_prompt` 新增 `is_review`——复核轮提示词明确「重点 hold/adjust/sell 涨停持仓，非极高把握不出新买入信号」。
- 效果：封板保护后 **~10 分钟内**（下一 tick 提交 + LLM 分析时长）AI 即来复核。
