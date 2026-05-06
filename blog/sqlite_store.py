"""SQLite 存储：笔记与项目（启动时由 Markdown 同步）。"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# 默认：仓库根目录下 data/blog.db（与 blog/ 包并列）
_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = _ROOT / "data" / "blog.db"

SQLITE_PATH = os.getenv("SQLITE_PATH", str(DEFAULT_SQLITE_PATH))

_conn: sqlite3.Connection | None = None


def _date_to_ms(date_str: str) -> int:
    s = (date_str or "").strip()
    if not s:
        return 0
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    if "T" in s:
        dt = datetime.fromisoformat(s)
    else:
        dt = datetime.fromisoformat(f"{s}T00:00:00")
    if dt.tzinfo is None:
        return int(dt.replace(tzinfo=None).timestamp() * 1000)
    return int(dt.timestamp() * 1000)


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS notes (
            slug TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            date_iso TEXT NOT NULL,
            sort_ms INTEGER NOT NULL,
            tags_json TEXT NOT NULL,
            summary TEXT NOT NULL,
            body_md TEXT NOT NULL,
            html TEXT NOT NULL,
            toc_html TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_notes_sort ON notes(sort_ms DESC);
        CREATE TABLE IF NOT EXISTS projects (
            slug TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            date_iso TEXT NOT NULL,
            sort_ms INTEGER NOT NULL,
            tags_json TEXT NOT NULL,
            summary TEXT NOT NULL,
            body_md TEXT NOT NULL,
            html TEXT NOT NULL,
            toc_html TEXT NOT NULL DEFAULT '',
            repo_url TEXT NOT NULL DEFAULT '',
            demo_url TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_projects_sort ON projects(sort_ms DESC);
        """
    )
    conn.commit()
    _migrate_schema(conn)


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Add new columns that may not exist in older databases."""
    for col, col_type in [("toc_html", "TEXT"), ("source", "TEXT")]:
        for table in ("notes", "projects"):
            try:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {col} {col_type} NOT NULL DEFAULT ''"
                )
            except sqlite3.OperationalError:
                pass  # column already exists
    conn.commit()


def open_database() -> sqlite3.Connection:
    path = Path(SQLITE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def get_client() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = open_database()
    return _conn


def ping_db(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1").fetchone()
        return True
    except sqlite3.Error:
        return False


def save_note(
    conn: sqlite3.Connection,
    *,
    slug: str,
    title: str,
    date_iso: str,
    tags: list[str],
    summary: str,
    body_md: str,
    html: str,
    toc_html: str = "",
    source: str = "",
) -> None:
    ms = _date_to_ms(date_iso)
    conn.execute(
        """
        INSERT INTO notes (slug, title, date_iso, sort_ms, tags_json, summary, body_md, html, toc_html, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            title=excluded.title,
            date_iso=excluded.date_iso,
            sort_ms=excluded.sort_ms,
            tags_json=excluded.tags_json,
            summary=excluded.summary,
            body_md=excluded.body_md,
            html=excluded.html,
            toc_html=excluded.toc_html,
            source=excluded.source
        """,
        (
            slug,
            title,
            date_iso,
            ms,
            json.dumps(tags, ensure_ascii=False),
            summary or "",
            body_md,
            html,
            toc_html or "",
            source or "",
        ),
    )


def save_project(
    conn: sqlite3.Connection,
    *,
    slug: str,
    title: str,
    date_iso: str,
    tags: list[str],
    summary: str,
    body_md: str,
    html: str,
    toc_html: str = "",
    repo_url: str = "",
    demo_url: str = "",
    source: str = "",
) -> None:
    ms = _date_to_ms(date_iso)
    conn.execute(
        """
        INSERT INTO projects (slug, title, date_iso, sort_ms, tags_json, summary, body_md, html, toc_html, repo_url, demo_url, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            title=excluded.title,
            date_iso=excluded.date_iso,
            sort_ms=excluded.sort_ms,
            tags_json=excluded.tags_json,
            summary=excluded.summary,
            body_md=excluded.body_md,
            html=excluded.html,
            toc_html=excluded.toc_html,
            repo_url=excluded.repo_url,
            demo_url=excluded.demo_url,
            source=excluded.source
        """,
        (
            slug,
            title,
            date_iso,
            ms,
            json.dumps(tags, ensure_ascii=False),
            summary or "",
            body_md,
            html,
            toc_html or "",
            repo_url or "",
            demo_url or "",
            source or "",
        ),
    )


def delete_note(conn: sqlite3.Connection, slug: str) -> None:
    conn.execute("DELETE FROM notes WHERE slug=?", (slug,))


def delete_project(conn: sqlite3.Connection, slug: str) -> None:
    conn.execute("DELETE FROM projects WHERE slug=?", (slug,))


def list_note_slugs_by_date(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT slug FROM notes ORDER BY sort_ms DESC"
    ).fetchall()
    return [r[0] for r in rows]


def list_project_slugs_by_date(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT slug FROM projects ORDER BY sort_ms DESC"
    ).fetchall()
    return [r[0] for r in rows]


def _row_to_doc(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d.pop("sort_ms", None)
    tags_raw = d.pop("tags_json", "[]")
    try:
        tags = json.loads(tags_raw)
        if not isinstance(tags, list):
            tags = []
    except json.JSONDecodeError:
        tags = []
    d["tags"] = tags
    d["date"] = d.pop("date_iso", "") or ""
    return d


def get_note(conn: sqlite3.Connection, slug: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM notes WHERE slug=?", (slug,)).fetchone()
    if not row:
        return None
    return _row_to_doc(row)


def get_project(conn: sqlite3.Connection, slug: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM projects WHERE slug=?", (slug,)).fetchone()
    if not row:
        return None
    return _row_to_doc(row)


def list_notes_card(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT slug, title, date_iso AS date, tags_json, summary
        FROM notes ORDER BY sort_ms DESC
        """
    ).fetchall()
    cards: list[dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        try:
            tags = json.loads(d.get("tags_json") or "[]")
            if not isinstance(tags, list):
                tags = []
        except json.JSONDecodeError:
            tags = []
        cards.append(
            {
                "slug": d["slug"],
                "title": d.get("title") or d["slug"],
                "date": d.get("date") or "",
                "tags": tags,
                "summary": d.get("summary") or "",
            }
        )
    return cards


def list_projects_card(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT slug, title, date_iso AS date, tags_json, summary, repo_url, demo_url
        FROM projects ORDER BY sort_ms DESC
        """
    ).fetchall()
    cards: list[dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        try:
            tags = json.loads(d.get("tags_json") or "[]")
            if not isinstance(tags, list):
                tags = []
        except json.JSONDecodeError:
            tags = []
        cards.append(
            {
                "slug": d["slug"],
                "title": d.get("title") or d["slug"],
                "date": d.get("date") or "",
                "tags": tags,
                "summary": d.get("summary") or "",
                "repo_url": d.get("repo_url") or "",
                "demo_url": d.get("demo_url") or "",
            }
        )
    return cards


def sync_cleanup_removed(
    conn: sqlite3.Connection,
    *,
    note_slugs: set[str],
    project_slugs: set[str],
) -> None:
    cur = conn.cursor()
    if note_slugs:
        qs = ",".join("?" * len(note_slugs))
        cur.execute(f"DELETE FROM notes WHERE slug NOT IN ({qs})", tuple(note_slugs))
    else:
        cur.execute("DELETE FROM notes")
    if project_slugs:
        qs = ",".join("?" * len(project_slugs))
        cur.execute(
            f"DELETE FROM projects WHERE slug NOT IN ({qs})", tuple(project_slugs)
        )
    else:
        cur.execute("DELETE FROM projects")
    conn.commit()


@dataclass
class DbStatus:
    ok: bool
    path: str


def db_status(conn: sqlite3.Connection) -> DbStatus:
    p = str(SQLITE_PATH)
    if len(p) > 80:
        p = "…" + p[-76:]
    return DbStatus(ok=ping_db(conn), path=p)
