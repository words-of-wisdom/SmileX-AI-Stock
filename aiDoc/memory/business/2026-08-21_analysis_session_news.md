# 大盘/板块分析接入近期资讯 + 新增早盘(9:20)分析时段

## 需求描述

1. 大盘/板块分析需结合近期资讯进行：分析数据注入近 24 小时重点财经资讯（复用已有 `business_news` 表，`news.sync_all` 每 5 分钟同步，无需新增抓取），资讯按发布时间倒序取前 30 条（标题｜源｜摘要前80字），作为独立章节拼入 user prompt，收集失败不阻塞分析。
2. 新增早盘分析策略（交易日 9:20 竞价阶段自动生成），前端在两页面报告区顶部加「收盘分析（默认）/ 早盘分析」tab 切换时段；原分析即收盘分析。

## 状态

已完成（2026-08-21）

## 涉及范围

### 后端
- **迁移 0024**：`business_analysis_run`/`business_analysis_config` 新增 `session` 列（close-收盘/morning-早盘，server_default 'close'，存量数据自动归为收盘）；config 唯一索引 `analysis_type` → `(analysis_type, session)`；run 去重索引扩展为 `(analysis_type, run_date, session)`。
- **Schema**：`SESSION_TYPES`/`SESSION_TYPE_NAMES` + `AnalysisSessionQuery`；Run/Config Item 加 session 字段。
- **接口**：`run / config(GET,PUT) / latest / runs` 五接口统一加 `session` query 参数（默认 close，兼容存量调用）。
- **执行器**：`submit_run`/`_execute_analysis`/`_analyze` 透传 session（并发守卫与去重按 类型+时段）；新增 `_collect_recent_news`；新增早盘系统提示词（`_MARKET_MORNING_SYSTEM_PROMPT`/`_SECTOR_MORNING_SYSTEM_PROMPT` + 早盘今日展望章节框架），数据=昨日收盘快照+近24h资讯，侧重隔夜消息面→今日开盘影响；`_build_system_prompt(type, session, include_tomorrow)` 按时段选组；早盘研判语义为「今日展望」（JSON 复用 tomorrow_outlook 字段，前端按时段换标签）。数据章节措辞由「当日」改「最新收盘」以兼容早盘语境。
- **定时任务**：`analysis.auto_generate`（16:05 close）+ 新增 `analysis.morning_generate`（cron `20 9 * * mon-fri`），共用 `_generate_for_types(session)`，同日同类型同时段去重。
- **种子**：`seed_analysis_strategy.py` 扩展为 4 条配置（market/sector × close/morning），补高水准早盘策略（消息-板块映射、开盘三情景推演、竞价确认信号）。
- 坑：MappedAsDataclass 模型新增带 default 的列不能放在无 default 列之前（dataclass 报 non-default argument follows default），`session` 放在 `run_date` 之后。

### 前端
- `typings/api/analysis.d.ts`：`SessionType = 'close' | 'morning'`；Run/Config 加 session。
- `service/api/analysis.ts`：run/latest/runs/config 四组函数加可选 session 参数（close 不传=后端默认）。
- `analysis-report-panel.vue`：新增 `session` prop 全链路透传；研判标签 close=明日研判 / morning=今日展望；策略抽屉标题分时段。
- 两页面右侧报告区加 `NTabs`（收盘分析/早盘分析），`:key="session"` 强制重建面板以重置轮询与历史状态；面板根卡片 `h-full` 改 `flex-1 min-h-0` 适配 flex 列容器。
- i18n：sessionClose/sessionMorning/todayOutlookLabel/morningStrategyTitle。

## 2026-08-21 二次追加：策略按时段彻底分离 + 资讯考量强化

- 策略定位明确：**收盘=当日复盘+明日预判**（角色定位改"当日市场复盘与次日预判/当日板块复盘与次日轮动预判"），**早盘=只针对当日**（"当日开盘前瞻（只针对今日，不做隔日预判）"）；两者配置本就独立（0024 唯一键 类型+时段），本次将定位差异落到提示词与 UI 文案
- 资讯考量强化：
  - 收盘系统提示词报告结构新增「消息面复盘/消息面与板块印证」章节（资讯与盘面背离必须点出并解释：兑现出货/预期抢跑/情绪压制）
  - 收盘种子策略新增"消息面复盘"纪律（印证强化结论、背离点出、纯消息异动标脉冲）；早盘策略强化消息-板块映射的"影响时效"（竞价脉冲/半日/全天）
  - 资讯注入段 prompt 增加指令：按影响力分级（宏观>行业>个股）、相似资讯合并、关联弱的忽略、引用原文
- 前端策略抽屉按时段分离全部文案：研判开关标签（明日研判/今日展望）、开关说明、主策略/研判提示词 placeholder 各一套（i18n：includeTodayOutlook/todayPromptLabel/morningPromptPlaceholder 等）；抽屉底部新增「资讯结合」说明（注入近24h资讯30条，策略可约定资讯筛选侧重/影响力分级/消息-板块映射）
