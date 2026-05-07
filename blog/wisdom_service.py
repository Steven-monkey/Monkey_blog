"""智慧箴言服务 —— LLM 生成箴言、调用生图 API、下载外部图片。

由 routes_wisdom.py 调用，不直接处理 HTTP 请求/响应。
所有函数返回纯数据或 (bytes, content_type) 元组。
"""

import base64
import json
import random

import requests

from blog.config import (
    DOWNLOAD_HTTP_TIMEOUT_SECONDS,
    FALLBACK_QUOTES,
    HTTP_SESSION,
    IMAGE_API_BASE,
    IMAGE_API_KEY,
    IMAGE_FALLBACK_HEIGHT,
    IMAGE_FALLBACK_WIDTH,
    IMAGE_HEIGHT,
    IMAGE_HTTP_TIMEOUT_SECONDS,
    IMAGE_MODEL,
    IMAGE_WIDTH,
    LLM_API_KEY,
    LLM_API_URL,
    LLM_HTTP_TIMEOUT_SECONDS,
    LLM_MODEL,
    _normalize_api_url,
)


def fallback_quote(note: str = ""):
    """从本地箴言库随机取一条。"""
    item = random.choice(FALLBACK_QUOTES)
    result = {"text": item["text"], "author": item["author"], "source": "fallback"}
    if note:
        result["note"] = note
    return result


def request_llm_quote():
    """调用 LLM 生成一句箴言 + 视觉提示词（JSON mode）。"""
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
        '{"quote":"箴言内容","author":"作者/文化标签","visual_prompt":"中文视觉描述"}'
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


def build_fallback_visual_prompt(text: str, author: str) -> str:
    """生成通用视觉提示词（无特定箴言信息时使用）。"""
    return (
        f"9:16竖屏艺术摄影，电影级光影，柔和焦外，色彩温柔而富有生命力，意境深邃。"
        f"主题围绕箴言：{text.strip()}；文化灵感：{(author or '未知来源').strip()}；"
        "壮丽自然场景，抽象意境，无文字无人物，高质量，精美壁纸。"
    )


def compose_quote_background(text: str, author: str, visual_prompt: str = "") -> dict:
    """拼装背景图信息：生成 prompt → URL 编码 → 返回 image_url 等字段。"""
    prompt = (visual_prompt or "").strip() or build_fallback_visual_prompt(text, author)
    from urllib.parse import quote
    prompt_encoded = quote(prompt, safe="")
    return {
        "image_url": f"/api/wisdom/render-image?prompt={prompt_encoded}",
        "image_prompt": prompt,
        "image_width": IMAGE_WIDTH,
        "image_height": IMAGE_HEIGHT,
        "image_ratio": "9:16",
    }


def fetch_remote_image(image_url: str) -> tuple[bytes, str]:
    """下载远程图片，返回 (bytes, content_type)。"""
    headers = {"User-Agent": "wisdom-site/1.0"}
    if IMAGE_API_KEY:
        headers["Authorization"] = f"Bearer {IMAGE_API_KEY}"
        headers["x-api-key"] = IMAGE_API_KEY
    response = HTTP_SESSION.get(
        image_url, headers=headers, timeout=DOWNLOAD_HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    body = response.content
    content_type = (
        response.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
    )
    return body, content_type


def build_openai_images_url() -> str:
    """构建生图 API 完整 URL（兼容多种 base URL 格式）。"""
    base = IMAGE_API_BASE.rstrip("/")
    if base.endswith("/images/generations"):
        return base
    if base.endswith("/v1") or base.endswith("/api/v3"):
        return f"{base}/images/generations"
    return f"{base}/images/generations"


def request_openai_image_with_size(
    prompt: str, width: int, height: int
) -> tuple[bytes, str]:
    """调用兼容 OpenAI 的生图 API，返回 (bytes, content_type)。"""
    payload = {"prompt": prompt, "n": 1, "size": f"{width}x{height}"}
    if IMAGE_MODEL:
        payload["model"] = IMAGE_MODEL

    headers = {"Content-Type": "application/json", "User-Agent": "wisdom-site/1.0"}
    if IMAGE_API_KEY:
        headers["Authorization"] = f"Bearer {IMAGE_API_KEY}"
        headers["x-api-key"] = IMAGE_API_KEY

    response = HTTP_SESSION.post(
        build_openai_images_url(),
        json=payload, headers=headers, timeout=IMAGE_HTTP_TIMEOUT_SECONDS,
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
        return fetch_remote_image(image_url)
    if b64_data:
        return base64.b64decode(b64_data), "image/png"
    raise ValueError("image api 未返回 url 或 b64_json")


def render_image_bytes(prompt: str) -> tuple[bytes, str]:
    """按主尺寸调用生图。"""
    return request_openai_image_with_size(prompt, IMAGE_WIDTH, IMAGE_HEIGHT)


def render_image_bytes_with_fallback(prompt: str) -> tuple[bytes, str]:
    """生图：主尺寸失败时自动尝试回退尺寸。"""
    try:
        return render_image_bytes(prompt)
    except (
        requests.exceptions.RequestException, KeyError, ValueError,
        json.JSONDecodeError, base64.binascii.Error,
    ) as primary_err:
        # 如果主尺寸和回退尺寸相同，不需要重试
        if (IMAGE_WIDTH == IMAGE_FALLBACK_WIDTH
                and IMAGE_HEIGHT == IMAGE_FALLBACK_HEIGHT):
            raise primary_err
        try:
            return request_openai_image_with_size(
                prompt, IMAGE_FALLBACK_WIDTH, IMAGE_FALLBACK_HEIGHT
            )
        except (
            requests.exceptions.RequestException, KeyError, ValueError,
            json.JSONDecodeError, base64.binascii.Error,
        ) as fallback_err:
            raise ValueError(
                f"主尺寸({IMAGE_WIDTH}x{IMAGE_HEIGHT})失败: {primary_err}; "
                f"回退尺寸({IMAGE_FALLBACK_WIDTH}x{IMAGE_FALLBACK_HEIGHT})失败: {fallback_err}"
            ) from fallback_err
