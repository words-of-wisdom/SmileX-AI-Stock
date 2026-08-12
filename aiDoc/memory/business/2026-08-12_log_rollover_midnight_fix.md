# 调试模式日志按天划分（when='D' 改 'MIDNIGHT' + 归档目录清理）

## 需求描述

用户反馈：调试模式（本地 dev）也需要实现日志按天划分。排查发现本地 `backend/logs/app.log`
从 8 月 9 日到 8 月 12 日累计 701MB，跨越多个午夜从未滚动，也没有生成任何日期归档目录。

根因（两层）：

1. **`when='D'` 不是按自然日切分**：`TimedRotatingFileHandler` 的 `'D'` 表示「handler 创建
   时刻 + 24 小时」滚动一次（实测 rolloverAt = 启动时刻 + 24h，如 15:06 → 次日 15:06），
   而非午夜。要按自然日 00:00 切分必须用 `'MIDNIGHT'`。
2. **重启即重置计时**：rolloverAt 在 handler 创建时计算。调试模式 `uvicorn --reload`
   每次保存代码都重启子进程，rolloverAt 被重置为「重启时刻 + 24h」。活跃开发期间几乎每天
   都有重启，滚动计时永远到不了触发点，日志文件无限增长。

连带发现：旧记录（2026-07-11）声称「`backupCount` 由 TimedRotatingFileHandler 自动清理
最旧的日期目录」——**这是错的**。父类 `getFilesToDelete` 只匹配日志根目录下的
`base.log.YYYY-MM-DD` 后缀文件，感知不到 `YYYY-MM-DD/` 子目录，日期归档永远不会被清理。

## 状态

已完成

## 涉及范围

### 后端

- `backend/config/logging_dev.ini`：`devFileHandler` 的 `when` 由 `'D'` 改为 `'MIDNIGHT'`，
  滚动点固定为每天 00:00，进程重启不再重置滚动节奏（重启后仍指向当天午夜）。
- `backend/config/logging_prod.ini`：`infoFileHandler` / `errorFileHandler` 同步改为
  `'MIDNIGHT'`（生产原本能滚动但按「启动时刻 + 24h」切，归档日期跨两天且错位）。
- `backend/gunicorn.conf.py`：`access_file` / `error_file` 的 `when` 同步改为 `'MIDNIGHT'`。
- `backend/core/log/daily_dir_handler.py`：`DailyDirFileHandler` 新增 `doRollover` 重写
  + `_prune_expired_date_dirs`，滚动后按 `backupCount` 删除最旧的 `YYYY-MM-DD/` 目录
  （`shutil.rmtree(ignore_errors=True)` 容忍多 worker 并发清理竞争）；类/模块 docstring
  补充 `'MIDNIGHT'` 使用约束。

### 前端

无

## 约束与备注

- `'MIDNIGHT'` 与 `'D'` 的归档后缀同为 `%Y-%m-%d`，`rotation_filename` 的日期目录转换
  逻辑无需改动。
- 机器在午夜休眠时，滚动顺延到唤醒后的第一条日志触发，该条日志本身仍写入新文件，
  只有触发前的少量跨午夜日志会落在前一天归档内——标准库固有行为，可接受。
- `backupCount` 语义不变（dev 14 天 / prod 90 天），只是清理对象从「后缀文件」修正为
  「日期目录」。同一日志根目录下多个 handler（info/error/access/gunicorn-error）的
  backupCount 配置一致，清理结果一致，互不冲突。
- 验证方式：fileConfig 加载 dev/prod ini 后 rolloverAt 均为次日 00:00:00；强制滚动后
  归档落入 `YYYY-MM-DD/app.log`；backupCount=2 时 4 个历史日期目录仅保留最新 2 个。
- 运行中的旧进程需重启才能加载新配置；已有的 701MB `app.log` 不会自动切分，如需归档
  历史可手动按日期切割移入对应日期目录。

## 相关文件

- `backend/config/logging_dev.ini`
- `backend/config/logging_prod.ini`
- `backend/gunicorn.conf.py`
- `backend/core/log/daily_dir_handler.py`

## 记录日期

2026-08-12
