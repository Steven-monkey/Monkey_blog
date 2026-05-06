"""系统路由：健康检查、LLM 状态。"""

from flask import Blueprint, jsonify

from blog.config import (
    IMAGE_API_BASE,
    IMAGE_API_KEY,
    IMAGE_HEIGHT,
    IMAGE_MODEL,
    IMAGE_WIDTH,
    LLM_API_KEY,
    LLM_MODEL,
)
from blog.db import get_db
from blog.sqlite_store import ping_db

system_bp = Blueprint("system", __name__)


@system_bp.get("/healthz")
def healthz():
    conn = get_db()
    ok = ping_db(conn)
    return jsonify({"ok": True, "sqlite": ok})


@system_bp.get("/api/llm/status")
@system_bp.get("/api/deepseek/status")
def llm_status():
    return jsonify(
        {
            "configured": bool(LLM_API_KEY),
            "quote_model": LLM_MODEL,
            "image_model": IMAGE_MODEL or "default",
            "image_provider": "openai-compatible",
            "image_api_base": IMAGE_API_BASE,
            "image_configured": bool(IMAGE_API_KEY),
            "image_size": f"{IMAGE_WIDTH}x{IMAGE_HEIGHT}",
        }
    )
