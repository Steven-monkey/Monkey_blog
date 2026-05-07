"""SSR 页面路由 —— 首页、笔记、项目、AI搜索、智慧箴言页面。

所有页面路由注册在 content_bp Blueprint 下。
渲染数据来自 SQLite（启动时已从 Markdown 同步）。
"""

from flask import Blueprint, abort, render_template

from blog import sqlite_store
from blog.config import AUTHOR_NAME
from blog.db import get_db

content_bp = Blueprint("content", __name__)


@content_bp.get("/")
def blog_home():
    """首页：个人信息 + 最新笔记/项目预览。"""
    conn = get_db()
    notes = sqlite_store.list_notes_card(conn)
    projects = sqlite_store.list_projects_card(conn)
    st = sqlite_store.db_status(conn)
    return render_template(
        "home.html",
        notes=notes,
        projects=projects,
        notes_count=len(notes),
        projects_count=len(projects),
        author_name=AUTHOR_NAME,
        db_ok=st.ok,
    )


@content_bp.get("/notes")
def notes_list():
    """笔记列表：按日期倒序时间线展示。"""
    conn = get_db()
    items = sqlite_store.list_notes_card(conn)
    return render_template("notes_list.html", items=items)


@content_bp.get("/notes/<slug>")
def note_detail(slug: str):
    """单篇笔记详情。"""
    conn = get_db()
    doc = sqlite_store.get_note(conn, slug)
    if not doc:
        abort(404)
    return render_template("note_detail.html", doc=doc)


@content_bp.get("/projects")
def projects_list():
    """项目列表：按日期倒序时间线展示。"""
    conn = get_db()
    items = sqlite_store.list_projects_card(conn)
    return render_template("projects_list.html", items=items)


@content_bp.get("/projects/<slug>")
def project_detail(slug: str):
    """单个项目详情。"""
    conn = get_db()
    doc = sqlite_store.get_project(conn, slug)
    if not doc:
        abort(404)
    return render_template("project_detail.html", doc=doc)


@content_bp.get("/playground/wisdom")
def wisdom_page():
    """智慧箴言独立全屏页面。"""
    return render_template("wisdom.html")


@content_bp.get("/ai/search")
def ai_search_page():
    """AI 智能搜索页面。"""
    return render_template("ai_search.html")
