"""数据库启动与连接管理。

bootstrap_db() 在应用启动时执行：
1. 打开 SQLite 连接
2. 同步 content/ 下本地 Markdown → SQLite
3. 如果配置了 GitHub，同步远程 Markdown → SQLite
"""

import logging

from blog import content_sync
from blog import sqlite_store

logger = logging.getLogger(__name__)

_db = None


def get_db():
    """获取 SQLite 连接实例（单例）。"""
    if _db is None:
        raise RuntimeError("数据库未初始化")
    return _db


def bootstrap_db():
    """应用启动入口：建库 + 内容同步。"""
    global _db
    _db = sqlite_store.get_client()

    # 本地 Markdown 同步
    n_notes, n_projects = content_sync.sync_all(_db)

    # GitHub 远程笔记同步（可选，通过 GITHUB_REPO 环境变量启用）
    from blog import github_sync
    n_github = 0
    if github_sync.GITHUB_ENABLED:
        try:
            n_github = github_sync.sync_github(_db)
        except Exception as e:
            logger.warning("GitHub 同步失败: %s", e)

    logger.info(
        "已同步 %s 篇本地笔记、%s 个本地项目、%s 篇 GitHub 笔记",
        n_notes, n_projects, n_github,
    )
