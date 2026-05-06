"""SSR 页面路由。"""

from flask import Blueprint, abort, render_template

from blog import sqlite_store
from blog.db import get_db

content_bp = Blueprint("content", __name__)


@content_bp.get("/")
def blog_home():
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
        db_ok=st.ok,
    )


@content_bp.get("/notes")
def notes_list():
    conn = get_db()
    items = sqlite_store.list_notes_card(conn)
    return render_template("notes_list.html", items=items)


@content_bp.get("/notes/<slug>")
def note_detail(slug: str):
    conn = get_db()
    doc = sqlite_store.get_note(conn, slug)
    if not doc:
        abort(404)
    return render_template("note_detail.html", doc=doc)


@content_bp.get("/projects")
def projects_list():
    conn = get_db()
    items = sqlite_store.list_projects_card(conn)
    return render_template("projects_list.html", items=items)


@content_bp.get("/projects/<slug>")
def project_detail(slug: str):
    conn = get_db()
    doc = sqlite_store.get_project(conn, slug)
    if not doc:
        abort(404)
    return render_template("project_detail.html", doc=doc)


@content_bp.get("/playground/wisdom")
def wisdom_page():
    return render_template("wisdom.html")


@content_bp.get("/ai/search")
def ai_search_page():
    return render_template("ai_search.html")
