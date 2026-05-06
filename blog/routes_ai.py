"""AI API 路由：智能搜索、阅读助手、内容推荐。"""

from flask import Blueprint, Response, jsonify, request, stream_with_context

from blog import ai_service
from blog.db import get_db

ai_bp = Blueprint("ai", __name__)


@ai_bp.post("/api/ai/search")
def api_ai_search():
    data = request.get_json(silent=True) or {}
    query = (data.get("q") or "").strip()
    if not query:
        return jsonify({"error": "查询内容不能为空"}), 400
    conn = get_db()
    result = ai_service.ai_search(conn, query)
    return jsonify(result)


@ai_bp.post("/api/ai/chat")
def api_ai_chat():
    data = request.get_json(silent=True) or {}
    content_type = data.get("content_type", "")
    slug = data.get("slug", "")
    message = (data.get("message") or "").strip()
    history = data.get("history", [])

    if not content_type or not slug or not message:
        return jsonify({"error": "缺少必要参数"}), 400
    if content_type not in ("note", "project"):
        return jsonify({"error": "无效的内容类型"}), 400

    conn = get_db()

    def event_stream():
        for chunk in ai_service.ai_chat_stream(
            conn, content_type, slug, message, history
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@ai_bp.post("/api/ai/recommend")
def api_ai_recommend():
    data = request.get_json(silent=True) or {}
    content_type = data.get("type", "")
    slug = data.get("slug", "")
    limit = min(int(data.get("limit", 3)), 10)

    if not content_type or not slug:
        return jsonify({"error": "缺少必要参数"}), 400
    if content_type not in ("note", "project"):
        return jsonify({"error": "无效的内容类型"}), 400

    conn = get_db()
    items = ai_service.get_recommendations(conn, content_type, slug, limit)
    return jsonify({"items": items})


@ai_bp.get("/api/ai/status")
def api_ai_status():
    return jsonify(ai_service.ai_status())
