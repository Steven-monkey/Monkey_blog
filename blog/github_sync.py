"""GitHub 笔记同步 —— 从远程仓库拉取 Markdown 写入 SQLite。

通过 GitHub API 获取指定仓库中 .md 文件的内容，
解析 YAML Front Matter + 渲染 Markdown，存入 SQLite。
标记 source="github" 以区分本地笔记。

环境变量：
  GITHUB_REPO    - 仓库路径（owner/repo）
  GITHUB_TOKEN   - GitHub Personal Access Token
  GITHUB_PATH    - 仓库内 Markdown 文件所在目录（默认 content/notes）
  GITHUB_BRANCH  - 分支名（默认 main）
"""

from __future__ import annotations

import base64
import logging
import os
import sqlite3
from pathlib import Path

import frontmatter
import requests

from blog import sqlite_store as store
from blog.content_sync import _default_summary_from_md, _parse_tags, _render_html

logger = logging.getLogger(__name__)

# ── 环境变量 ──────────────────────────────────────────
GITHUB_REPO = os.getenv("GITHUB_REPO", "").strip()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_PATH = os.getenv("GITHUB_PATH", "content/notes").strip("/")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip()
SOURCE_TAG = "github"

GITHUB_ENABLED = bool(GITHUB_REPO)
_API_BASE = "https://api.github.com"


def _headers() -> dict[str, str]:
    """构建 GitHub API 请求头。"""
    h = {"Accept": "application/vnd.github.v3+json", "User-Agent": "blog-sync/1.0"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def _date_from_meta_or_fallback(meta: dict, default_date: str) -> str:
    """从 front matter 提取日期，无则用默认值。"""
    from datetime import date, datetime
    d = meta.get("date")
    if d is None:
        return default_date
    if isinstance(d, datetime):
        return d.date().isoformat()
    if isinstance(d, date):
        return d.isoformat()
    s = str(d).strip()
    return s[:10] if len(s) >= 10 else s


def _fetch_md_files() -> list[dict]:
    """通过 GitHub API 递归获取仓库树，下载所有 .md 文件并解析。

    返回列表，每项包含 slug/title/date_iso/tags/summary/body_md/html/toc_html/source。
    """
    if not GITHUB_ENABLED:
        return []

    # 1. 获取仓库文件树
    url = f"{_API_BASE}/repos/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    tree = resp.json().get("tree") or []

    # 2. 筛选指定目录下的 .md 文件
    prefix = GITHUB_PATH + "/"
    md_entries = [
        item for item in tree
        if item.get("type") == "blob"
        and item["path"].startswith(prefix)
        and item["path"].endswith(".md")
    ]

    # 3. 逐个下载并解析
    results = []
    for entry in md_entries:
        file_url = f"{_API_BASE}/repos/{GITHUB_REPO}/contents/{entry['path']}?ref={GITHUB_BRANCH}"
        file_resp = requests.get(file_url, headers=_headers(), timeout=30)
        if file_resp.status_code != 200:
            logger.warning("GitHub 文件读取失败 %s: HTTP %s", entry["path"], file_resp.status_code)
            continue

        data = file_resp.json()
        content_b64 = data.get("content") or ""
        if not content_b64:
            continue

        # Base64 解码 + UTF-8 → Markdown
        raw_text = base64.b64decode(content_b64).decode("utf-8")

        # 解析 Front Matter + 渲染
        post = frontmatter.loads(raw_text)
        meta = dict(post.metadata)
        body = (post.content or "").strip()

        slug = str(meta.get("slug") or Path(entry["path"]).stem).strip()
        title = str(meta.get("title") or slug).strip()
        date_iso = _date_from_meta_or_fallback(meta, "2026-01-01")
        tags = _parse_tags(meta)
        summary = str(meta.get("summary") or _default_summary_from_md(body)).strip()
        html, toc_html = _render_html(body)

        results.append({
            "slug": slug,
            "title": title,
            "date_iso": date_iso,
            "tags": tags,
            "summary": summary,
            "body_md": body,
            "html": html,
            "toc_html": toc_html,
            "source": SOURCE_TAG,
        })

    return results


def sync_github(conn: sqlite3.Connection) -> int:
    """从 GitHub 拉取 Markdown 并写入 SQLite。返回同步条数。"""
    files = _fetch_md_files()
    for f in files:
        store.save_note(
            conn,
            slug=f["slug"],
            title=f["title"],
            date_iso=f["date_iso"],
            tags=f["tags"],
            summary=f["summary"],
            body_md=f["body_md"],
            html=f["html"],
            toc_html=f.get("toc_html", ""),
            source=f.get("source", SOURCE_TAG),
        )
    conn.commit()
    return len(files)
