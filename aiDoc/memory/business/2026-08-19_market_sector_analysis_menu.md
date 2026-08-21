# AI分析目录新增大盘/板块分析菜单

## 需求描述

在「AI助手」目录（/ai）下、与「AI 分析」平级，新增「大盘分析」「板块分析」两个菜单。页面形态为数据摘要 + AI 分析：大盘分析页展示指数快照与资金流摘要并配合 AI 大盘点评；板块分析页展示行业/概念板块涨幅榜并配合 AI 板块轮动解读。AI 分析为落库型异步执行（对齐策略 run 模式），支持历史回看与收盘后定时自动生成。板块成分股（板块→个股映射）本期不做。

**2026-08-19 追加（迁移 0022）**：增加大盘和板块的分析策略配置 + 明日研判：
- 分析策略作为可配置项，入口在报告面板「历史记录」按钮旁（「分析策略」抽屉：策略提示词 textarea + 明日研判开关）
- 新表 `business_analysis_config`（analysis_type 唯一）：`prompt_template`（策略定制提示词，空=默认策略）+ `include_tomorrow`（明日研判开关，默认开）
- 明日研判开启时系统提示词追加「明日研判」章节要求（大盘：方向/关键信号位/应对建议；板块：轮动延续/高低切换/退潮判断），JSON 摘要增加 `tomorrow_outlook {direction, summary}`，前端摘要区展示研判徽章（方向 tag + 摘要）
- 为支撑研判质量增强数据注入：market 加上证指数近 10 日走势；sector 加近 3 个交易日行业涨幅榜 TOP5 对比（轮动延续性）
- 新接口 `GET/PUT /admin/analysis/{analysis_type}/config`（GET 无记录返默认值而非 null；PUT 权限 `analysis:strategy`，BUTTON 8018/8019）
- 关闭明日研判时 executor 会丢弃 LLM 可能误输出的 tomorrow_outlook 字段
- 坑：update_config 在裸 AsyncSession（expire_on_commit=True）下 commit 后 `model_validate(ORM)` 触发 MissingGreenlet，改为直接从请求构造响应规避

**2026-08-19 二次追加（迁移 0023）**：明日研判也支持定制提示词：
- `business_analysis_config` 新增 `tomorrow_prompt_template` 列（include_tomorrow 开启时注入 user prompt「明日研判策略要求」段，优先级高于默认框架；空则用内置专业框架）
- 内置研判框架升级为专业方法论：多空证据清单（禁止单边叙事）+ 三情景概率推演（触发条件→概率合计100%→应对）+ 作废条件（可证伪信号）；开启研判时报告长度上限放宽至 1200 字；JSON 的 tomorrow_outlook.summary 须包含核心依据与可验证确认信号
- 前端抽屉加「明日研判提示词」输入框（仅研判开关开启时显示，保存时关闭研判则该字段清空）
- 高水准策略已通过 `backend/scripts/seed_analysis_strategy.py`（幂等）写入 market/sector 两类型配置：主策略（卖方策略分析师/买方轮动研究员角色定位 + 证据分级 + 分析纪律）+ 明日策略（定位先行/阶段定位 + 三情景概率推演 + 作废条件）
- 页面布局改为左右两栏预览（可滚动）：根容器 `h-full flex gap-16px overflow-hidden lt-sm:flex-col lt-sm:overflow-auto`；左右卡片均为 `h-full flex flex-col` + `content-style="flex: 1 1 0%; overflow-y: auto;"` 实现头部固定、内容区独立滚动（NCard 用 content-style 滚动内容而非滚整卡）；大盘左栏 w-2/5（指数网格 cols 2/l:3）、板块左栏 w-1/2（表格 scroll-x 780 适配窄列），右栏报告面板 flex-1 min-w-0；lt-sm 回落上下堆叠（卡片 lt-sm:h-auto + 根 overflow-auto 整页滚动）
- 金额单位统一：共用 `views/ai/utils.ts` 的 `fmtAmountCn`（≥1亿→X.XX亿；≥1千万→X.XX千万；≥1万→X.X万；负数按绝对值分级保留负号），替换两页面各自的 fmtMoney（此前阈值/精度不一致）
- 大盘页增加同上一交易日比较：内容区顶部比较块——两市成交额环比（`fetchGetMarketDates` 取真实上一交易日→`fetchGetMarketIndices(prevDate)` 汇总昨日成交额，显示 `昨日→今日 + 放量/缩量+涨幅%` 标签，涨红跌绿）+ 主力净流入环比（资金流近5日倒数第二条，显示 `昨日→今日 + 增减额`）；无上一日数据时整块隐藏；指数卡片涨跌幅本身即相对昨收无需重复比较

## 状态

已完成

## 涉及范围

### 后端

- 新模块 `backend/modules/analysis/`（前缀 `/admin/analysis`，复用 agent 的 `llm_client.resolve_model` + `stream_chat`，不走 ReAct 工具循环，数据直接注入 prompt 单轮生成）
  - `POST /{analysis_type}/run`（手动触发生成，异步返回 `{run_id, status: "running"}`，权限 `analysis:run`）
  - `GET /{analysis_type}/latest`（最新一条含报告原文，无记录 data 为 null）
  - `GET /{analysis_type}/runs`（分页历史，`analysis_type` 为 path 参数 market/sector）
  - `GET /runs/{run_id}`（详情）
- 新表 `business_analysis_run`（迁移 0021）：`analysis_type`(market/sector)、`run_date`、`trigger_type`(schedule/manual)、`status` 三态 running/success/failed（对齐 0020 后策略 run）、`ai_raw_response`（markdown 报告原文）、`parsed_result`（JSON 摘要：大盘 `{sentiment,score,summary,key_points}`，板块 `{rotation_summary,hot_boards[],key_points}`）、`error_msg`
- 执行器 `AnalysisExecutor`：同 type running 并发守卫（错误码 11603 ANALYSIS_ALREADY_RUNNING，新错误码段 11601-11603）、独立 session 后台任务、600s 超时兜底；数据来源：market 用 `MarketService.get_indices/get_fund_flow` + `LimitUpService.get_stats`，sector 用 `BoardService.get_list`（行业/概念涨幅榜 TOP15）
- LLM 场景：`AiFunctionEnum.TREND_PREDICTION`（LLM配置页可为趋势预测绑专属模型）；系统提示词要求先输出 ```json 摘要块再输出 markdown 报告，JSON 解析失败仅摘要为空不影响报告
- 调度任务 `analysis.auto_generate`：cron `5 16 * * mon-fri`（在 market 15:30/board 15:31/limit_up 15:35 同步完成后），同日同类型已有记录则跳过
- 菜单种子（迁移 0021，挂 AI 目录 8001 下）：8012 `ai_market-analysis`（MENU，sort 4）、8013 `ai_sector-analysis`（MENU，sort 5）+ 4 个 BUTTON（8014-8017，共享权限码 `analysis:list`/`analysis:run`，读接口统一 `analysis:list` 因 require_permission 只认 BUTTON 类型权限）；不写 sys_role_menu（惯例：超管免授权，其他角色上线后勾选）

### 前端

- 新页面 `views/ai/market-analysis/index.vue`（指数卡片 NGrid + 资金流摘要 + 报告面板）、`views/ai/sector-analysis/index.vue`（行业/概念 NRadioGroup 切换涨幅榜 TOP20 + 报告面板）
- 共用组件 `views/ai/components/analysis-report-panel.vue`（views/ai 下无 index.vue 的 components 目录不生成路由）：生成按钮（hasAuth analysis:run）→ 提交后 5s 轮询 latest → 情绪/温度徽章（market）或轮动总结/热门板块（sector）+ markdown-it 渲染正文 + 历史记录抽屉分页回看
- 新 API `service/api/analysis.ts` + 类型 `typings/api/analysis.d.ts`；指数/资金流/板块数据复用现有 stock-market/stock-board API
- i18n：route 键 `ai_market-analysis`/`ai_sector-analysis` + `page.aiAnalysis.*`（zh/en + app.d.ts Schema 同步）；`pnpm gen-route` 生成四件套

## 约束与备注

- **sys_menu.name 必须与前端 elegant-router 生成的路由 name 逐字一致**（`ai_market-analysis`/`ai_sector-analysis`，连字符保留、层级下划线连接），否则菜单不可见或 404（0018 踩坑）
- 报告正文渲染前需剥离开头的 ```json 摘要代码块（组件内正则处理）
- 前端轮询仅在最新记录 status=running 时进行（5s 间隔），完成即停
- 板块分析数据基于现有板块日快照（涨跌幅/成交额/主力净流入/领涨股/涨跌家数），成分股下钻、北向资金等新数据源本期不做

## 相关文件

- 后端：`backend/modules/analysis/`（endpoints/services/schemas/router，含 analysis_config_service.py）、`backend/database/models/business/analysis.py`（Run + Config 两模型）、`backend/alembic/versions/0021_add_market_sector_analysis.py`、`backend/alembic/versions/0022_add_analysis_config.py`、`backend/modules/scheduler/tasks/analysis_run.py`、`backend/core/response/response_code.py`、`backend/main.py`
- 前端：`frontend/src/views/ai/market-analysis/index.vue`、`frontend/src/views/ai/sector-analysis/index.vue`、`frontend/src/views/ai/components/analysis-report-panel.vue`、`frontend/src/service/api/analysis.ts`、`frontend/src/typings/api/analysis.d.ts`、`frontend/src/locales/langs/{zh-cn,en-us}.ts`、`frontend/src/typings/app.d.ts`、`frontend/src/router/elegant/*`（生成）

## 记录日期

2026-08-19

**2026-08-21 追加**：分析接入近24h重点资讯 + 新增早盘(9:20)分析时段，见 [2026-08-21 记录](./2026-08-21_analysis_session_news.md)。
