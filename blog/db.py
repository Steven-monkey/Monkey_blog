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
    logger.info("已同步 %s 篇笔记、%s 个项目到 SQLite", n_notes, n_projects)
