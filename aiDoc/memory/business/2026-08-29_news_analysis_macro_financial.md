# 每日资讯分析 + 宏观指数 + 财报解读

## 需求描述

三大新能力（迁移 0026）：

1. **AI 每日资讯分析**：早盘（交易日 9:25）+ 周日晚（20:30）两个时段对聚合资讯做分类解读，区分「宏观经济/行业资讯」与「个股资讯」两个分类，各不超过 10 条
2. **企业财报获取/解读/预测**：持仓+策略标的定时自动解读 + 任意股票手动查询解读，AI 输出财报质量评级/亮点/风险/下期预测
3. **宏观经济指数板块**：中美 CPI/PPI/M1/M2 等指标独立展示（卡片+走势图）+ 注入 AI 分析（大盘/资讯）

## 状态

已完成（2026-08-29）

## 涉及范围

### 后端

- analysis 模块扩展：`ANALYSIS_TYPES` 加 `news`、`SESSION_TYPES` 加 `weekly`，类型×时段组合校验（`VALID_TYPE_SESSIONS`）；`analysis_executor.py` 新增 news 两套 system prompt + `_collect_macro_context()` 宏观注入（market/news，失败可摘除降级）
- 新模块 `modules/macro/`：akshare 抓取（中国 CPI/PPI/货币供应、美国 CPI）→ `business_macro_indicator` upsert；任务 `macro.sync_all`（每日 07:30）
- 新模块 `modules/financial/`：akshare 新浪财务指标抓取 → `business_financial_report`；`FinancialService.submit_interpretation` 异步 AI 解读（与 AnalysisExecutor 同模式：三态 + 并发守卫 + 后台任务强引用）；任务 `financial.auto_interpret`（工作日 08:00，持仓+近30天信号标的，同报告期去重）
- 新表：`business_macro_indicator` / `business_financial_report` / `business_financial_interpretation`
- 错误码：11621（macro）、11641-11644（financial）；main.py 注册两路由 + 两调度任务

### 前端

- 新页面：`views/ai/news-analysis/`（morning/weekly tab，复用 analysis-report-panel）、`views/ai/macro/`（中美 tab + 指标卡片 + ECharts）、`views/ai/financial-analysis/`（代码查询 + 解读报告 + 指标表 + 历史列表）
- `analysis-report-panel.vue` 扩展 news 类型渲染（两个分类列表卡片，各 ≤10 条；策略抽屉隐藏研判开关）
- 新 API：`service/api/macro.ts`、`financial.ts`；类型 `Api.Macro.*` / `Api.Financial.*` / `Api.Analysis.NewsParsedResult`
- 菜单（迁移 0026）：`ai_news-analysis`（复用 analysis 权限）、`ai_financial-analysis`（financial:list/run）、`ai_macro`（macro:list/sync）

## 约束与备注

- news 分析 morning 取近 24h 资讯 60 条、weekly 取近 7 天 120 条（素材量大于输出上限，供 LLM 筛选）
- APScheduler 星期字段必须写 `sun`/`mon-fri`（数字是错位的）
- MappedAsDataclass 新表字段顺序：无默认值字段必须在有默认值字段之前（BusinessFinancialReport/Interpretation 踩过）
- 迁移菜单插入用逐行 insert（bulk_insert 首行键编译列丢值坑）
- 宏观/财报 akshare 列名做容错映射（上游列名偶有调整）
- 财报解读 LLM 复用 `analysis_executor._run_llm`（TREND_PREDICTION 函数模型）

## 相关文件

- `backend/modules/analysis/services/analysis_executor.py`（news prompt + 宏观注入）
- `backend/modules/macro/`、`backend/modules/financial/`
- `backend/modules/scheduler/tasks/analysis_run.py` / `macro_sync.py` / `financial_run.py`
- `backend/alembic/versions/0026_macro_financial_news.py`
- `frontend/src/views/ai/news-analysis/`、`macro/`、`financial-analysis/`
- `aiDoc/frontend-backend/boundary.md`（新增三段契约）

## 记录日期

2026-08-29
