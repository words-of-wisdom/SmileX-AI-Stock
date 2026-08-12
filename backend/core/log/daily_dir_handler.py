#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按日期目录组织的滚动日志 Handler。

继承 ``logging.handlers.TimedRotatingFileHandler``，在每天滚动时把日志文件移入
``YYYY-MM-DD/`` 子目录，而不是生成 ``.YYYY-MM-DD`` 后缀文件。

注意：必须配合 ``when='MIDNIGHT'`` 使用才是按自然日切分。``when='D'`` 的滚动点
是「handler 创建时刻 + 24 小时」，进程一重启计时就会重置，开发模式（uvicorn
reload 频繁重启）下滚动可能永远不触发。
"""

import logging.handlers
import re
import shutil
from pathlib import Path

# 日期归档目录名，如 2026-07-11
_DATE_DIR_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class DailyDirFileHandler(logging.handlers.TimedRotatingFileHandler):
    """按日期目录存放历史日志的 TimedRotatingFileHandler。

    示例：
        当前活动日志：``/var/log/smilex_cloud/access.log``
        滚动后归档：``/var/log/smilex_cloud/2026-07-11/access.log``
    """

    def rotation_filename(self, default_name: str) -> str:
        """将默认滚动文件名 ``base.log.YYYY-MM-DD`` 转换为 ``YYYY-MM-DD/base.log``。

        Args:
            default_name: 父类计算出的默认滚动文件名，含日期后缀。

        Returns:
            转换后的绝对路径字符串。
        """
        path = Path(default_name)
        # default_name 形如 /path/to/access.log.2026-07-11
        date_part = path.suffix.lstrip(".")  # YYYY-MM-DD
        base_name = path.stem  # access.log
        base_dir = path.parent  # /path/to

        date_dir = base_dir / date_part
        date_dir.mkdir(parents=True, exist_ok=True)

        target = date_dir / base_name
        # 与标准 TimedRotatingFileHandler 行为保持一致：目标已存在时先删除
        if target.exists():
            target.unlink()

        return str(target)

    def doRollover(self):
        """滚动完成后，按 ``backupCount`` 清理最旧的日期目录。

        父类的 ``getFilesToDelete`` 只识别日志根目录下的 ``base.log.YYYY-MM-DD``
        后缀文件，感知不到日期子目录，因此保留天数的清理由本类自行实现。
        """
        super().doRollover()
        self._prune_expired_date_dirs()

    def _prune_expired_date_dirs(self) -> None:
        """删除超出 ``backupCount`` 保留天数的最旧日期目录。"""
        if self.backupCount <= 0:
            return
        base_dir = Path(self.baseFilename).parent
        # YYYY-MM-DD 目录名字典序即时间序
        date_dirs = sorted(
            p
            for p in base_dir.iterdir()
            if p.is_dir() and _DATE_DIR_PATTERN.match(p.name)
        )
        excess = len(date_dirs) - self.backupCount
        for old_dir in date_dirs[: max(excess, 0)]:
            # 多进程（如 Gunicorn 多 worker）可能同时清理同一目录，忽略竞争错误
            shutil.rmtree(old_dir, ignore_errors=True)
