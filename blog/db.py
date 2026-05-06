"""数据库启动与连接管理。"""

import logging

from blog import content_sync
from blog import sqlite_store

logger = logging.getLogger(__name__)

_db = None


def get_db():
    if _db is None:
        raise RuntimeError("数据库未初始化")
    return _db


def bootstrap_db():
    global _db
    _db = sqlite_store.get_client()
    n_notes, n_projects = content_sync.sync_all(_db)

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
