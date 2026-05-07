"""全局配置 —— 环境变量加载、HTTP 会话、回退数据。

所有模块通过 `from blog.config import XXX` 获取配置，
避免在多处重复读取 os.getenv。
"""

import os

from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests

# 项目启动时立即加载 .env
load_dotenv()

# ═══════════════════════════════════════════════════════════
# LLM 配置（文本生成：箴言、AI搜索、阅读助手等共用）
# ═══════════════════════════════════════════════════════════
LLM_API_URL = (
    os.getenv("LLM_API_URL")
    or os.getenv("DEEPSEEK_API_URL")
    or "https://api.deepseek.com/chat/completions"
)
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or ""
LLM_MODEL = os.getenv("LLM_MODEL") or os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"

# ═══════════════════════════════════════════════════════════
# 生图配置（智慧箴言背景图生成）
# ═══════════════════════════════════════════════════════════
IMAGE_API_BASE = os.getenv("IMAGE_API_BASE") or "https://api.openai.com/v1"
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "").strip()
IMAGE_API_KEY = os.getenv("IMAGE_API_KEY", "").strip()
IMAGE_WIDTH = int(os.getenv("IMAGE_WIDTH", "1080"))
IMAGE_HEIGHT = int(os.getenv("IMAGE_HEIGHT", "1920"))
# 生图回退尺寸：主尺寸 API 不支持时自动重试
IMAGE_FALLBACK_WIDTH = int(os.getenv("IMAGE_FALLBACK_WIDTH", "1440"))
IMAGE_FALLBACK_HEIGHT = int(os.getenv("IMAGE_FALLBACK_HEIGHT", "2560"))

# ═══════════════════════════════════════════════════════════
# 超时配置（秒）
# ═══════════════════════════════════════════════════════════
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

# ═══════════════════════════════════════════════════════════
# 服务器 & 博客展示
# ═══════════════════════════════════════════════════════════
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
AUTHOR_NAME = os.getenv("AUTHOR_NAME", "Monkey")

# ═══════════════════════════════════════════════════════════
# 回退箴言库 —— AI 服务不可用时使用
# ═══════════════════════════════════════════════════════════
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


def _normalize_api_url(raw_url: str) -> str:
    """统一 API 地址格式：确保以 /chat/completions 结尾。"""
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


def _build_retry_session() -> requests.Session:
    """创建带重试策略的 HTTP 会话，应对网络抖动。"""
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


# 全局共享的 HTTP 会话（含重试）
HTTP_SESSION = _build_retry_session()
