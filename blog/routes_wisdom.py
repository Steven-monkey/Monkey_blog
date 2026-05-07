"""智慧箴言 API 路由 —— LLM 箴言生成、生图、下载、代理。

全部注册在 wisdom_bp Blueprint 下。
"""

import base64
import json
from datetime import datetime
from io import BytesIO
from urllib.parse import parse_qs, unquote, urlparse

import requests
from flask import Blueprint, jsonify, request, send_file

from blog.config import LLM_API_KEY
from blog.wisdom_service import (
    compose_quote_background,
    fallback_quote,
    fetch_remote_image,
    render_image_bytes_with_fallback,
    request_llm_quote,
)

wisdom_bp = Blueprint("wisdom", __name__)


@wisdom_bp.get("/api/llm/wisdom")
@wisdom_bp.get("/api/deepseek/wisdom")
def llm_wisdom():
    """AI 生成箴言 + 背景图 URL。失败自动回退到本地箴言库。"""
    if not LLM_API_KEY:
        fallback_data = fallback_quote("AI 服务未配置，已返回本地经典箴言。")
        fallback_data.update(
            compose_quote_background(fallback_data["text"], fallback_data["author"])
        )
        return jsonify(fallback_data)

    try:
        data = request_llm_quote()
        data.update(
            compose_quote_background(
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
        fallback_data = fallback_quote(f"AI 服务请求失败: {err}")
        fallback_data.update(
            compose_quote_background(fallback_data["text"], fallback_data["author"])
        )
        return jsonify(fallback_data)


@wisdom_bp.get("/api/wisdom/background")
def wisdom_background():
    """根据箴言文本生成背景图描述和 URL。"""
    text = (request.args.get("text") or "").strip()
    author = (request.args.get("author") or "").strip()
    if not text:
        return jsonify({"error": "query param 'text' is required"}), 400
    return jsonify(compose_quote_background(text, author))


@wisdom_bp.get("/api/wisdom/download-image")
def download_image():
    """下载外部图片（如 Pollinations.ai 生成的图）。"""
    image_url = (request.args.get("url") or "").strip()
    if not image_url:
        return jsonify({"error": "query param 'url' is required"}), 400
    if not image_url.startswith(("http://", "https://")):
        return jsonify({"error": "invalid image url"}), 400
    try:
        body, content_type = fetch_remote_image(image_url)
    except requests.exceptions.RequestException as err:
        return jsonify({"error": f"download failed: {err}"}), 502

    ext_map = {"image/png": "png", "image/webp": "webp", "image/gif": "gif"}
    ext = ext_map.get(content_type, "jpg")
    filename = f"wisdom-bg-{datetime.now().strftime('%Y%m%d-%H%M%S')}.{ext}"
    return send_file(
        BytesIO(body), mimetype=content_type,
        as_attachment=True, download_name=filename,
    )


@wisdom_bp.get("/api/wisdom/image-proxy")
def image_proxy():
    """图片代理 —— 支持外链和本地 render-image 递归渲染。"""
    image_url = (request.args.get("url") or "").strip()
    if not image_url:
        return jsonify({"error": "query param 'url' is required"}), 400
    if not image_url.startswith(("http://", "https://")):
        return jsonify({"error": "invalid image url"}), 400

    parsed = urlparse(image_url)
    # 如果是渲染路径，走生图流程
    if parsed.path == "/api/wisdom/render-image":
        query_params = parse_qs(parsed.query or "")
        prompt = (query_params.get("prompt", [""])[0] or "").strip()
        if prompt:
            try:
                body, content_type = render_image_bytes_with_fallback(unquote(prompt))
                return send_file(BytesIO(body), mimetype=content_type)
            except (
                requests.exceptions.RequestException, KeyError,
                ValueError, json.JSONDecodeError, base64.binascii.Error,
            ) as err:
                return jsonify({"error": f"fetch image failed: {err}"}), 502

    # 否则直接代理外链图片
    try:
        body, content_type = fetch_remote_image(image_url)
    except requests.exceptions.RequestException as err:
        return jsonify({"error": f"fetch image failed: {err}"}), 502
    return send_file(BytesIO(body), mimetype=content_type)


@wisdom_bp.get("/api/wisdom/render-image")
def render_image():
    """调用生图 API 渲染图片（主尺寸失败自动回退）。"""
    prompt = (request.args.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "query param 'prompt' is required"}), 400
    try:
        body, content_type = render_image_bytes_with_fallback(prompt)
    except (
        requests.exceptions.RequestException, KeyError,
        ValueError, json.JSONDecodeError, base64.binascii.Error,
    ) as err:
        return jsonify({"error": f"render image failed: {err}"}), 502
    return send_file(BytesIO(body), mimetype=content_type)
