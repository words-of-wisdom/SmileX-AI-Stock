# 开盘后大盘/板块AI分析显示昨日数据

## 需求描述

用户反馈：每天开盘后，大盘/板块 AI 分析页面一直显示昨天的数据，没有及时刷新为当日早盘分析。

## 状态

已完成

## 根因诊断（三层叠加）

1. **早盘任务当天未部署**（一次性）：`analysis.morning_generate`（9:20）为 2026-08-21 上午新功能，当天 11 点后才随服务重启注册（查 `sys_scheduled_task.last_run_at=None` 证实从未执行），9:20 时任务不存在 → 当天无 morning 记录。
2. **LLM 422 敏感词无降级**（持续性）：morning 分析把近 24h 资讯原文注入 prompt，MiniMax 内容审核命中敏感词（`input new_sensitive (1026)`）直接 422 拒绝整单 → 分析 failed。资讯为外部抓取内容不可控，随时可能复现。
3. **任务失败无补跑**（持续性）：`_generate_for_types` 去重条件为"当天已有任意记录（含 failed）则跳过"，且 cron 单点触发（`20 9`）→ 当天一旦失败全天缺报告，页面只能显示旧数据。

顺带发现独立 bug：`strategy.trade_engine` cron 误写 8 字段（`* * * * * 9-15 * * mon-fri`），`CronTrigger.from_crontab` 解析失败被 `_build_trigger` 吞掉（仅记 error 日志）→ **交易引擎 job 从未注册、从未执行过**（DB `last_run_at=None` 证实）。热榜同步链路（stock_hot）经查当天全程正常，非本次问题。

## 涉及范围

### 后端

- `modules/analysis/services/analysis_executor.py`：
  - 资讯注入从 `_collect_market_data`/`_collect_sector_data` 内部移出，`_analyze` 单独收集拼装（置于行情数据段之前）
  - LLM 调用改两段式：首次失败且注入了资讯 → 摘除资讯段降级重试一次（替代段注明"消息面数据缺失，请在报告中注明"），二次仍失败才标 failed
- `modules/scheduler/tasks/analysis_run.py`：
  - 去重条件改为 `status.in_(("success", "running"))`——failed 不阻塞当日重试（running 仍跳过防并发；600s 超时最晚 9:30/16:15 定格，能被补跑点接住）
  - cron 补跑点：morning `20 9` → `20,35 9`；close `5 16` → `5,25 16`
- `modules/scheduler/tasks/strategy_run.py`：trade_engine cron 修正为 `* 9-15 * * mon-fri`（重启时 `sync_registry_to_db` 用代码定义覆盖 DB 并重建 job）

### 前端

无（报告面板已有 running 轮询、failed 展示、手动生成；`latest` 按 created_at 倒序取最新，补跑成功后自然展示）

## 约束与备注

- 降级重试只摘资讯段，行情数据（结构化数字）保留——它不触发内容审核
- 敏感词 422 是随资讯窗口滑动的概率事件（同日 11:47 失败、15:50 成功），降级是兜底而非必经路径
- ⚠️ 行为变化：trade_engine 修复后首次真正开始每分钟执行（模拟买卖/止损止盈平仓），存量待执行信号会开始被真实执行
- cron 定义以代码为准：启动时 `sync_registry_to_db` 会覆盖 DB 中的 cron_expression，改调度只需改装饰器参数

## 验证结果（2026-08-21 盘后实测）

- 热重载后三个任务 cron 均同步，`next_run_at` 非空：morning→下周一 9:20、close→当日 16:05、trade_engine→1 分钟后
- 真实触发 market/sector morning 分析各一次：均 success（9703/7210 字符，摘要解析成功），前端 morning tab 即刻有当日数据
- mock LLM 首调失败验证降级分支：2 次调用（首次含资讯、重试含缺失注明且无资讯）→ success
- trade_engine 15:50 起连续执行 success（当前无待执行信号，skipped 属预期）

## 相关文件

- `backend/modules/analysis/services/analysis_executor.py`
- `backend/modules/scheduler/tasks/analysis_run.py`
- `backend/modules/scheduler/tasks/strategy_run.py`

## 记录日期

2026-08-21
