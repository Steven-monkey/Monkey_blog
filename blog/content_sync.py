"""从 content/ 下 Markdown 同步到 SQLite。"""
from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import frontmatter
import markdown

from blog import ai_service
from blog import sqlite_store as store

_AI_AVAILABLE = ai_service.AI_ENABLED

# 仓库根目录（与 blog/ 并列的 content/）
ROOT_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT_DIR / "content"
NOTES_DIR = CONTENT_DIR / "notes"
PROJECTS_DIR = CONTENT_DIR / "projects"

MD_EXTENSIONS = ["extra", "toc", "sane_lists", "codehilite"]


def _default_summary_from_md(text: str, max_len: int = 160) -> str:
    plain = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    plain = re.sub(r"`[^`]+`", " ", plain)
    plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", plain)
    plain = re.sub(r"[#>*_\-]+", " ", plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    if len(plain) <= max_len:
        return plain
    return plain[: max_len - 1].rstrip() + "…"


def _render_html(md_body: str) -> tuple[str, str]:
    md = markdown.Markdown(extensions=MD_EXTENSIONS)
    body_html = md.convert(md_body)
    toc_html = getattr(md, 'toc', '') or ''
    return body_html, toc_html if toc_html.strip() else ''


def _parse_tags(meta: dict) -> list[str]:
    raw = meta.get("tags")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        return [p.strip() for p in raw.split(",") if p.strip()]
    return []


def _slug_from_meta_or_file(meta: dict, path: Path) -> str:
    s = meta.get("slug")
    if s and str(s).strip():
        return str(s).strip()
    return path.stem


def _date_from_meta(meta: dict, path: Path) -> str:
    d = meta.get("date")
    if d is None:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    if isinstance(d, datetime):
        return d.date().isoformat()
    if isinstance(d, date):
        return d.isoformat()
    s = str(d).strip()
    return s[:10] if len(s) >= 10 else s


def _load_md_dir(directory: Path) -> list[tuple[Path, dict, str]]:
    if not directory.exists():
        return []
    out: list[tuple[Path, dict, str]] = []
    for path in sorted(directory.glob("*.md")):
        post = frontmatter.load(path)
        meta = dict(post.metadata)
        body = (post.content or "").strip()
        out.append((path, meta, body))
    return out


def _maybe_enrich_with_ai(
    title: str, body: str, meta: dict
) -> tuple[list[str], str]:
    """如果 front matter 缺少 tags 或 summary，尝试用 AI 生成。"""
    tags = _parse_tags(meta)
    summary = str(meta.get("summary") or "").strip()

    if _AI_AVAILABLE:
        if not tags:
            try:
                tags = ai_service.auto_generate_tags(title, body)
            except Exception:
                pass
        if not summary:
            try:
                summary = ai_service.auto_generate_summary(title, body)
            except Exception:
                pass

    return tags, summary or _default_summary_from_md(body)


def sync_all(conn: sqlite3.Connection) -> tuple[int, int]:
    """将磁盘 Markdown 写入 SQLite，并删除已移除文件的条目。"""
    note_slugs: set[str] = set()
    project_slugs: set[str] = set()

    for path, meta, body in _load_md_dir(NOTES_DIR):
        slug = _slug_from_meta_or_file(meta, path)
        note_slugs.add(slug)
        title = str(meta.get("title") or slug).strip()
        date_iso = _date_from_meta(meta, path)
        tags, summary = _maybe_enrich_with_ai(title, body, meta)
        html, toc_html = _render_html(body)
        store.save_note(
            conn,
            slug=slug,
            title=title,
            date_iso=date_iso,
            tags=tags,
            summary=summary,
            body_md=body,
            html=html,
            toc_html=toc_html,
        )

    for path, meta, body in _load_md_dir(PROJECTS_DIR):
        slug = _slug_from_meta_or_file(meta, path)
        project_slugs.add(slug)
        title = str(meta.get("title") or slug).strip()
        date_iso = _date_from_meta(meta, path)
        tags, summary = _maybe_enrich_with_ai(title, body, meta)
        html, toc_html = _render_html(body)
        repo_url = str(meta.get("repo") or meta.get("repo_url") or "").strip()
        demo_url = str(meta.get("demo") or meta.get("demo_url") or "").strip()
        store.save_project(
            conn,
            slug=slug,
            title=title,
            date_iso=date_iso,
            tags=tags,
            summary=summary,
            body_md=body,
            html=html,
            toc_html=toc_html,
            repo_url=repo_url,
            demo_url=demo_url,
        )

    store.sync_cleanup_removed(
        conn, note_slugs=note_slugs, project_slugs=project_slugs
    )
    return len(note_slugs), len(project_slugs)
