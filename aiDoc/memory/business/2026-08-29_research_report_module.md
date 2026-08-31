# 券商研报采集 + 研报中心 + 研报掘金策略

## 需求描述

两大新能力（迁移 0027）：

1. **研报采集与概览**：基于 akshare 东财接口（`stock_research_report_em`）按股票采集券商研报（标题/机构/评级/盈利预测 EPS·PE/行业/日期/PDF 链接），提供研报中心页面（近30天统计卡片 + 评级分布 + 热门股票/机构 TOP10 + 可筛选列表）
2. **基于研报的个股分析策略**：预置策略「研报掘金」（seq=12，category=general，pre_market 时段），Agent 新增 `get_research_reports`/`get_report_consensus` 两个工具供 LLM 查研报做买卖研判；用户将股票池设为某一只个股即实现「对某个公司分析」

## 状态

已完成（2026-08-29）

## 涉及范围

### 后端

- 新模块 `modules/research/`：`research_fetcher.py`（akshare 东财研报抓取，列名映射「报告名称/东财评级/机构/YYYY-盈利预测-收益|市盈率/日期/报告PDF链接」，截取近 60 条）+ `research_service.py`（按 url upsert 去重、分页列表筛选、get_stats 概览统计、collect_sync_codes 持仓+近30天信号标的收集、空库 FALLBACK_CODES 兜底）
- 新表：`business_research_report`（uk url 去重，ix stock_code+published_date）
- 定时任务：`research.sync_reports`（每 4 小时）
- Agent 工具：`modules/agent/tools/research_report_tools.py`（get_research_reports / get_report_consensus，已加入 strategy_executor SYSTEM_PROMPT 工具清单与 agent_service 导入）
- 预置策略：迁移 0027 幂等插入「研报掘金」（ID 2942406616009112，默认停用）
- 错误码 11661-11662（research）；main.py 注册路由 + 调度任务

### 前端

- 新页面 `views/ai/research-report/index.vue`（统计卡片/评级分布 tag/热门 TOP 点击筛选/remote 分页表格 flex-height/手动同步按钮）
- 新 API `service/api/research.ts`；类型 `Api.Research.*`
- 菜单（迁移 0027）：`ai_research-report`（research:list / research:sync，ID 8029-8031）

## 踩坑记录

- **MappedAsDataclass 字段顺序**：必填列必须写在可选列之前，否则 dataclass 报 `non-default argument follows default`
- **Date 列不能直接塞字符串**：asyncpg 报 `'str' object has no attribute 'toordinal'`，service 层须 `date.fromisoformat()` 转换
- **SQLAlchemy Result 只能消费一次**：`.all()` 第二次调用返回空列表，需先物化 `rating_counts = rows.all()`
- 东财接口无作者/目标价/摘要字段，forecast 为 {年份: {eps, pe}}
