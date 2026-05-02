import json
import os
import random
import base64
from datetime import datetime
from io import BytesIO
from urllib.parse import parse_qs, quote, unquote, urlparse

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    jsonify,
    render_template,
    request,
    send_file,
    Response,
    stream_with_context,
)
import requests

from blog import ai_service
from blog import content_sync
from blog import sqlite_store
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")

_db = None


def get_db():
    if _db is None:
        raise RuntimeError("数据库未初始化")
    return _db

# 通用 LLM 配置
LLM_API_URL = (
    os.getenv("LLM_API_URL")
    or os.getenv("DEEPSEEK_API_URL")
    or "https://api.deepseek.com/chat/completions"
)
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or ""
LLM_MODEL = os.getenv("LLM_MODEL") or os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"

# 生图配置 - 默认 9:16 竖屏 1080x1920
IMAGE_API_BASE = os.getenv("IMAGE_API_BASE") or "https://api.openai.com/v1"
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "").strip()
IMAGE_API_KEY = os.getenv("IMAGE_API_KEY", "").strip()
IMAGE_WIDTH = int(os.getenv("IMAGE_WIDTH", "1080"))
IMAGE_HEIGHT = int(os.getenv("IMAGE_HEIGHT", "1920"))
IMAGE_FALLBACK_WIDTH = int(os.getenv("IMAGE_FALLBACK_WIDTH", "1440"))
IMAGE_FALLBACK_HEIGHT = int(os.getenv("IMAGE_FALLBACK_HEIGHT", "2560"))
HTTP_TIMEOUT_SECONDS = int(os.getenv("HTTP_TIMEOUT_SECONDS", "45"))
LLM_HTTP_TIMEOUT_SECONDS = int(
    os.getenv("LLM_HTTP_TIMEOUT_SECONDS", os.getenv("HTTP_TIMEOUT_SECONDS", "45"))
)
IMAGE_HTTP_TIMEOUT_SECONDS = int(
    os.getenv("IMAGE_HTTP_TIMEOUT_SECONDS", os.getenv("HTTP_TIMEOUT_SECONDS", "45"))
)
DOWNLOAD_HTTP_TIMEOUT_SECONDS = int(
    os.getenv("DOWNLOAD_HTTP_TIMEOUT_SECONDS", os.getenv("HTTP_TIMEOUT_SECONDS", "45"))
)

FALLBACK_QUOTES = [
    {"text": "生命不是等待风暴过去，而是学会在雨中起舞。", "author": "维维安·格林"},
    {"text": "你生来就是一座火山，不要满足于只冒烟。", "author": "非洲谚语"},
    {"text": "不要因为走得太远，而忘记为什么出发。", "author": "纪伯伦"},
    {"text": "我本可以忍受黑暗，如果我不曾见过太阳。", "author": "艾米莉·狄金森"},
    {
        "text": "世界上只有一种真正的英雄主义，那就是在认清生活真相之后依然热爱生活。",
        "author": "罗曼·罗兰",
    },
]


def _build_retry_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


HTTP_SESSION = _build_retry_session()


@app.get("/")
def blog_home():
    conn = get_db()
    notes = sqlite_store.list_notes_card(conn)
    projects = sqlite_store.list_projects_card(conn)
    st = sqlite_store.db_status(conn)
    return render_template(
        "home.html",
        notes=notes,
        projects=projects,
        db_ok=st.ok,
    )


@app.get("/notes")
def notes_list():
    conn = get_db()
    items = sqlite_store.list_notes_card(conn)
    return render_template("notes_list.html", items=items)


@app.get("/notes/<slug>")
def note_detail(slug: str):
    conn = get_db()
    doc = sqlite_store.get_note(conn, slug)
    if not doc:
        abort(404)
    return render_template("note_detail.html", doc=doc)


@app.get("/projects")
def projects_list():
    conn = get_db()
    items = sqlite_store.list_projects_card(conn)
    return render_template("projects_list.html", items=items)


@app.get("/projects/<slug>")
def project_detail(slug: str):
    conn = get_db()
    doc = sqlite_store.get_project(conn, slug)
    if not doc:
        abort(404)
    return render_template("project_detail.html", doc=doc)


@app.get("/playground/wisdom")
def wisdom_page():
    return render_template("wisdom.html")


# ═══════════════════════════════════════════════════════════
# AI 博客功能路由
# ═══════════════════════════════════════════════════════════

@app.get("/ai/search")
def ai_search_page():
    """AI 智能搜索页面。"""
    return render_template("ai_search.html")


@app.post("/api/ai/search")
def api_ai_search():
    """AI 智能搜索 API。"""
    data = request.get_json(silent=True) or {}
    query = (data.get("q") or "").strip()
    if not query:
        return jsonify({"error": "查询内容不能为空"}), 400
    conn = get_db()
    result = ai_service.ai_search(conn, query)
    return jsonify(result)


@app.post("/api/ai/chat")
def api_ai_chat():
    """AI 阅读助手流式聊天 API (SSE)。"""
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


@app.post("/api/ai/recommend")
def api_ai_recommend():
    """AI 内容推荐 API。"""
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


@app.get("/api/ai/status")
def api_ai_status():
    """AI 服务状态。"""
    return jsonify(ai_service.ai_status())


@app.get("/healthz")
def healthz():
    conn = get_db()
    ok = sqlite_store.ping_db(conn)
    return jsonify({"ok": True, "sqlite": ok})


@app.get("/api/llm/status")
@app.get("/api/deepseek/status")
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


def _fallback_quote(note: str = ""):
    item = random.choice(FALLBACK_QUOTES)
    result = {
        "text": item["text"],
        "author": item["author"],
        "source": "fallback",
    }
    if note:
        result["note"] = note
    return result


def _normalize_api_url(raw_url: str) -> str:
    url = (raw_url or "").strip().rstrip("/")
    if not url:
        return "https://api.deepseek.com/chat/completions"
    if url.endswith("/chat/completions"):
        return url
    if url == "https://api.deepseek.com":
        return f"{url}/chat/completions"
    if url.endswith("/v1"):
        return f"{url}/chat/completions"
    return url


def _request_llm_quote():
    system_prompt = (
        "你是一位深谙生命力量的箴言大师，你的每一句话都能点燃灵魂。"
        "你从全球不同文明的智慧中汲取灵感，创作短小精悍、意象鲜明、充满生命力的哲理短句。"
        "句子要像一记重拳，直击心灵，或如一道闪电，照亮黑暗。"
    )
    user_prompt = (
        "用中文创作一句15～60字的箴言，要求：\n"
        "- 充满力量感与生命力，能够瞬间打动人心；\n"
        "- 使用生动的比喻或震撼的意象，避免陈词滥调；\n"
        "- 积极、向上，给予人勇气、希望或深刻洞察。\n\n"
        "同时，为这句箴言构思一幅精美的竖屏背景图，要求描述详细，包括："
        "光影、色彩、构图、情绪，必须与箴言意境完美契合，不出现文字，不出现人物特写。\n"
        "请严格按照以下JSON格式输出，不要添加任何额外内容：\n"
        '{"quote":"箴言内容","author":"作者/文化标签","visual_prompt":"中文视觉描述，适合生成高质感竖屏壁纸，包含电影级光影、柔和焦外等关键词"}'
    )
    payload = {
        "model": LLM_MODEL,
        "temperature": 0.9,
        "max_tokens": 250,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    request_url = _normalize_api_url(LLM_API_URL)
    response = HTTP_SESSION.post(
        request_url,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        },
        timeout=LLM_HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    raw = response.json()
    content = (
        raw.get("choices", [{}])[0].get("message", {}).get("content") or ""
    ).strip()

    try:
        parsed = json.loads(content)
        text = (parsed.get("quote") or parsed.get("text") or "").strip()
        author = parsed.get("author", "心灵共振").strip() or "心灵共振"
        visual_prompt = (parsed.get("visual_prompt") or "").strip()
    except json.JSONDecodeError:
        text = content.strip()
        author = "心灵共振"
        visual_prompt = ""

    if not text:
        raise ValueError("AI 服务返回了空内容")

    return {
        "text": text,
        "author": author,
        "source": "llm",
        "visual_prompt": visual_prompt,
    }


def _build_fallback_visual_prompt(text: str, author: str) -> str:
    quote_text = (text or "").strip()
    author_text = (author or "").strip() or "未知来源"
    return (
        f"9:16竖屏艺术摄影，电影级光影，柔和焦外，色彩温柔而富有生命力，意境深邃。"
        f"主题围绕箴言：{quote_text}；文化灵感：{author_text}；"
        "壮丽自然场景，抽象意境，无文字无人物，高质量，精美壁纸。"
    )


def _compose_quote_background(text: str, author: str, visual_prompt: str = "") -> dict:
    prompt = (visual_prompt or "").strip() or _build_fallback_visual_prompt(
        text, author
    )
    prompt_encoded = quote(prompt, safe="")
    return {
        "image_url": f"/api/wisdom/render-image?prompt={prompt_encoded}",
        "image_prompt": prompt,
        "image_width": IMAGE_WIDTH,
        "image_height": IMAGE_HEIGHT,
        "image_ratio": "9:16",
    }


def _fetch_remote_image(image_url: str) -> tuple[bytes, str]:
    headers = {"User-Agent": "wisdom-site/1.0"}
    if IMAGE_API_KEY:
        headers["Authorization"] = f"Bearer {IMAGE_API_KEY}"
        headers["x-api-key"] = IMAGE_API_KEY
    response = HTTP_SESSION.get(
        image_url,
        headers=headers,
        timeout=DOWNLOAD_HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    body = response.content
    content_type = (
        response.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
    )
    return body, content_type


def _request_openai_image_with_size(
    prompt: str, width: int, height: int
) -> tuple[bytes, str]:
    payload = {
        "prompt": prompt,
        "n": 1,
        "size": f"{width}x{height}",
    }
    if IMAGE_MODEL:
        payload["model"] = IMAGE_MODEL

    headers = {"Content-Type": "application/json", "User-Agent": "wisdom-site/1.0"}
    if IMAGE_API_KEY:
        headers["Authorization"] = f"Bearer {IMAGE_API_KEY}"
        headers["x-api-key"] = IMAGE_API_KEY

    response = HTTP_SESSION.post(
        _build_openai_images_url(),
        json=payload,
        headers=headers,
        timeout=IMAGE_HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    parsed = response.json()
    data_list = parsed.get("data") or []
    if not data_list:
        raise ValueError("image api 返回为空")

    first = data_list[0] or {}
    image_url = (first.get("url") or "").strip()
    b64_data = (first.get("b64_json") or "").strip()

    if image_url:
        return _fetch_remote_image(image_url)
    if b64_data:
        return base64.b64decode(b64_data), "image/png"
    raise ValueError("image api 未返回 url 或 b64_json")


def _build_openai_images_url() -> str:
    base = IMAGE_API_BASE.rstrip("/")
    if base.endswith("/images/generations"):
        return base
    if base.endswith("/v1") or base.endswith("/api/v3"):
        return f"{base}/images/generations"
    return f"{base}/images/generations"


def _render_image_bytes(prompt: str) -> tuple[bytes, str]:
    return _request_openai_image_with_size(prompt, IMAGE_WIDTH, IMAGE_HEIGHT)


def _render_image_bytes_with_fallback(prompt: str) -> tuple[bytes, str]:
    try:
        return _render_image_bytes(prompt)
    except (
        requests.exceptions.RequestException,
        KeyError,
        ValueError,
        json.JSONDecodeError,
        base64.binascii.Error,
    ) as primary_err:
        if (
            IMAGE_WIDTH == IMAGE_FALLBACK_WIDTH
            and IMAGE_HEIGHT == IMAGE_FALLBACK_HEIGHT
        ):
            raise primary_err
        try:
            return _request_openai_image_with_size(
                prompt, IMAGE_FALLBACK_WIDTH, IMAGE_FALLBACK_HEIGHT
            )
        except (
            requests.exceptions.RequestException,
            KeyError,
            ValueError,
            json.JSONDecodeError,
            base64.binascii.Error,
        ) as fallback_err:
            raise ValueError(
                f"主尺寸({IMAGE_WIDTH}x{IMAGE_HEIGHT})失败: {primary_err}; "
                f"回退尺寸({IMAGE_FALLBACK_WIDTH}x{IMAGE_FALLBACK_HEIGHT})失败: {fallback_err}"
            ) from fallback_err


@app.get("/api/llm/wisdom")
@app.get("/api/deepseek/wisdom")
def llm_wisdom():
    if not LLM_API_KEY:
        fallback_data = _fallback_quote("AI 服务未配置，已返回本地经典箴言。")
        fallback_data.update(
            _compose_quote_background(fallback_data["text"], fallback_data["author"])
        )
        return jsonify(fallback_data)

    try:
        data = _request_llm_quote()
        data.update(
            _compose_quote_background(
                data["text"], data["author"], data.get("visual_prompt", "")
            )
        )
        return jsonify(data)
    except (
        requests.exceptions.RequestException,
        KeyError,
        ValueError,
        json.JSONDecodeError,
    ) as err:
        fallback_data = _fallback_quote(f"AI 服务请求失败: {err}")
        fallback_data.update(
            _compose_quote_background(fallback_data["text"], fallback_data["author"])
        )
        return jsonify(fallback_data)


@app.get("/api/wisdom/background")
def wisdom_background():
    text = (request.args.get("text") or "").strip()
    author = (request.args.get("author") or "").strip()
    if not text:
        return jsonify({"error": "query param 'text' is required"}), 400
    return jsonify(_compose_quote_background(text, author))


@app.get("/api/wisdom/download-image")
def download_image():
    image_url = (request.args.get("url") or "").strip()
    if not image_url:
        return jsonify({"error": "query param 'url' is required"}), 400
    if not image_url.startswith(("http://", "https://")):
        return jsonify({"error": "invalid image url"}), 400
    try:
        body, content_type = _fetch_remote_image(image_url)
    except requests.exceptions.RequestException as err:
        return jsonify({"error": f"download failed: {err}"}), 502
    ext_map = {"image/png": "png", "image/webp": "webp", "image/gif": "gif"}
    ext = ext_map.get(content_type, "jpg")
    filename = f"wisdom-bg-{datetime.now().strftime('%Y%m%d-%H%M%S')}.{ext}"
    return send_file(
        BytesIO(body),
        mimetype=content_type,
        as_attachment=True,
        download_name=filename,
    )


@app.get("/api/wisdom/image-proxy")
def image_proxy():
    image_url = (request.args.get("url") or "").strip()
    if not image_url:
        return jsonify({"error": "query param 'url' is required"}), 400
    if not image_url.startswith(("http://", "https://")):
        return jsonify({"error": "invalid image url"}), 400
    parsed = urlparse(image_url)
    if parsed.path == "/api/wisdom/render-image":
        query_params = parse_qs(parsed.query or "")
        prompt = (query_params.get("prompt", [""])[0] or "").strip()
        if prompt:
            try:
                body, content_type = _render_image_bytes_with_fallback(unquote(prompt))
                return send_file(
                    BytesIO(body), mimetype=content_type, as_attachment=False
                )
            except (
                requests.exceptions.RequestException,
                KeyError,
                ValueError,
                json.JSONDecodeError,
                base64.binascii.Error,
            ) as err:
                return jsonify({"error": f"fetch image failed: {err}"}), 502
    try:
        body, content_type = _fetch_remote_image(image_url)
    except requests.exceptions.RequestException as err:
        return jsonify({"error": f"fetch image failed: {err}"}), 502
    return send_file(BytesIO(body), mimetype=content_type, as_attachment=False)


@app.get("/api/wisdom/render-image")
def render_image():
    prompt = (request.args.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "query param 'prompt' is required"}), 400
    try:
        body, content_type = _render_image_bytes_with_fallback(prompt)
    except (
        requests.exceptions.RequestException,
        KeyError,
        ValueError,
        json.JSONDecodeError,
        base64.binascii.Error,
    ) as err:
        return jsonify({"error": f"render image failed: {err}"}), 502
    return send_file(BytesIO(body), mimetype=content_type, as_attachment=False)


def bootstrap_db():
    global _db
    _db = sqlite_store.get_client()
    n_notes, n_projects = content_sync.sync_all(_db)
    app.logger.info("已同步 %s 篇笔记、%s 个项目到 SQLite", n_notes, n_projects)


bootstrap_db()

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    app.run(host=host, port=port)
