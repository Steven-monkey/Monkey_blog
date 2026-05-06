"""AI 博客服务层 —— 智能搜索、阅读助手、内容推荐、自动标签。"""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any, Generator

from blog import sqlite_store as store
from blog.config import (
    HTTP_SESSION,
    LLM_API_KEY,
    LLM_API_URL,
    LLM_HTTP_TIMEOUT_SECONDS,
    LLM_MODEL,
    _normalize_api_url,
)

AI_ENABLED = bool(LLM_API_KEY)

# ── AI 搜索结果缓存 ──────────────────────────────────────────
AI_SEARCH_CACHE_PREFIX = "blog:ai:search:"
AI_TAGS_CACHE_PREFIX = "blog:ai:tags:"
AI_SUMMARY_CACHE_PREFIX = "blog:ai:summary:"
AI_CACHE_TTL = 86400  # 1 天


def _llm_request(
    messages: list[dict],
    *,
    temperature: float = 0.7,
    max_tokens: int = 512,
    response_format: dict | None = None,
    stream: bool = False,
) -> dict | Generator[str, None, None]:
    """通用 LLM 请求封装，支持普通和流式模式。"""
    if not LLM_API_KEY:
        raise RuntimeError("AI 服务未配置 (LLM_API_KEY 为空)")

    payload = {
        "model": LLM_MODEL,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if response_format:
        payload["response_format"] = response_format
    if stream:
        payload["stream"] = True

    request_url = _normalize_api_url(LLM_API_URL)
    response = HTTP_SESSION.post(
        request_url,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        },
        timeout=LLM_HTTP_TIMEOUT_SECONDS,
        stream=stream,
    )
    response.raise_for_status()

    if stream:
        return _stream_response(response)
    else:
        raw = response.json()
        content = (
            raw.get("choices", [{}])[0].get("message", {}).get("content") or ""
        ).strip()
        return {"content": content}


def _stream_response(response: Any) -> Generator[str, None, None]:
    """解析 SSE 流式响应，逐 token 产出文本。"""
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        data_str = line[6:].strip()
        if data_str == "[DONE]":
            break
        try:
            chunk = json.loads(data_str)
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            token = delta.get("content", "")
            if token:
                yield token
        except json.JSONDecodeError:
            continue


# ═══════════════════════════════════════════════════════════
# 1. AI 智能搜索
# ═══════════════════════════════════════════════════════════

_PUNCTUATION_RE = re.compile(
    r"[，。！？、；：""''【】（）?!,.;]"
)


def _extract_keywords(query: str) -> list[str]:
    """用 LLM 从自然语言查询中提取搜索关键词。"""
    if not AI_ENABLED:
        # 降级：直接用中文分词式处理（简单按空格和标点切分）
        cleaned = _PUNCTUATION_RE.sub(" ", query)
        return [w.strip() for w in cleaned.split() if len(w.strip()) >= 2]

    prompt = (
        "你是一个博客搜索引擎的关键词提取器。\n"
        "请将用户的自然语言查询转化为3-5个搜索关键词，"
        "关键词应该是独立的名词或短语，能精准匹配博客文章。\n"
        "只输出 JSON 数组格式，例如：[\"Python\", \"Docker\", \"部署\"]\n"
        "不要输出任何其他文字。\n\n"
        f"用户查询: {query}"
    )
    try:
        result = _llm_request(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150,
            response_format={"type": "json_object"},
        )
        content = result["content"]
        # 尝试解析 JSON
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return [str(k).strip() for k in parsed if str(k).strip()]
        if isinstance(parsed, dict):
            for val in parsed.values():
                if isinstance(val, list):
                    return [str(k).strip() for k in val if str(k).strip()]
        return []
    except Exception:
        # 降级方案
        cleaned = _PUNCTUATION_RE.sub(" ", query)
        return [w.strip() for w in cleaned.split() if len(w.strip()) >= 2]


def _search_local(
    conn: sqlite3.Connection, keywords: list[str]
) -> list[dict[str, Any]]:
    """在本地库中按关键词搜索笔记和项目（标题、标签、摘要）。"""
    results: list[dict[str, Any]] = []

    # 搜索笔记
    note_slugs = store.list_note_slugs_by_date(conn)
    for slug in note_slugs:
        doc = store.get_note(conn, slug)
        if not doc:
            continue
        score = _calculate_match_score(doc, keywords)
        if score > 0:
            results.append({
                "type": "note",
                "slug": doc["slug"],
                "title": doc.get("title", ""),
                "summary": doc.get("summary", ""),
                "tags": doc.get("tags", []),
                "relevance_score": score,
            })

    # 搜索项目
    project_slugs = store.list_project_slugs_by_date(conn)
    for slug in project_slugs:
        doc = store.get_project(conn, slug)
        if not doc:
            continue
        score = _calculate_match_score(doc, keywords)
        if score > 0:
            results.append({
                "type": "project",
                "slug": doc["slug"],
                "title": doc.get("title", ""),
                "summary": doc.get("summary", ""),
                "tags": doc.get("tags", []),
                "relevance_score": score,
            })

    # 按相关性排序
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results


def _calculate_match_score(doc: dict, keywords: list[str]) -> float:
    """计算文档与关键词的相关性分数。"""
    score = 0.0
    title = (doc.get("title") or "").lower()
    summary = (doc.get("summary") or "").lower()
    tags = [t.lower() for t in (doc.get("tags") or [])]
    body = (doc.get("body_md") or "").lower()[:1000]  # 只检查前1000字符

    for kw in keywords:
        kw_lower = kw.lower()
        # 标题匹配（权重最高）
        if kw_lower in title:
            score += 3.0
        # 标签匹配（高权重）
        if any(kw_lower in tag for tag in tags):
            score += 2.5
        # 摘要匹配
        if kw_lower in summary:
            score += 1.5
        # 正文匹配
        count_in_body = body.count(kw_lower)
        if count_in_body > 0:
            score += min(count_in_body * 0.5, 2.0)

    return score


def _generate_ai_search_summary(
    query: str, results: list[dict], ai_enabled: bool
) -> tuple[str, list[dict]]:
    """AI 对搜索结果进行解读和增强。"""
    if not ai_enabled or not results:
        return "", results

    # 构建摘要信息供 LLM 分析
    items_text = "\n".join(
        f"- [{r['type']}] {r['title']}: {r['summary'][:80]}"
        for r in results[:5]
    )
    prompt = (
        "你是博客 AI 导读员。请对以下搜索结果用中文给出简洁的总体解读（50字内），"
        "并解释为什么这些结果与用户查询相关。\n\n"
        f"用户查询: {query}\n"
        f"搜索结果:\n{items_text}\n\n"
        "只输出解读文本，不要多余内容。"
    )
    try:
        result = _llm_request(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        ai_summary = result["content"].strip()
    except Exception:
        ai_summary = ""

    # 为每个结果生成 AI 解释
    enhanced_results = []
    for item in results[:10]:
        try:
            exp_prompt = (
                "用一句话（20字内）解释为什么以下内容与用户查询相关。\n"
                f"查询: {query}\n"
                f"标题: {item['title']}\n"
                f"摘要: {item['summary'][:60]}\n"
                "解释:"
            )
            exp_result = _llm_request(
                [{"role": "user", "content": exp_prompt}],
                temperature=0.3,
                max_tokens=80,
            )
            explanation = exp_result["content"].strip()
        except Exception:
            explanation = ""
        item["ai_explanation"] = explanation
        enhanced_results.append(item)

    return ai_summary, enhanced_results


def ai_search(conn: sqlite3.Connection, query: str) -> dict[str, Any]:
    """AI 智能搜索的完整流程。"""
    # 1. 提取关键词
    keywords = _extract_keywords(query)
    if not keywords:
        return {"query": query, "results": [], "ai_summary": "", "keywords": []}

    # 2. 本地搜索
    results = _search_local(conn, keywords)

    # 3. AI 增强
    ai_summary, enhanced_results = _generate_ai_search_summary(
        query, results, AI_ENABLED
    )

    return {
        "query": query,
        "keywords": keywords,
        "results": enhanced_results,
        "ai_summary": ai_summary,
    }


# ═══════════════════════════════════════════════════════════
# 2. AI 阅读助手（流式聊天）
# ═══════════════════════════════════════════════════════════

def _get_content_for_chat(
    conn: sqlite3.Connection, content_type: str, slug: str
) -> dict | None:
    """获取聊天上下文需要的文章内容。"""
    if content_type == "note":
        return store.get_note(conn, slug)
    if content_type == "project":
        return store.get_project(conn, slug)
    return None


def build_chat_messages(
    doc: dict, user_message: str, history: list[dict] | None = None
) -> list[dict]:
    """构建聊天消息序列。"""
    title = doc.get("title", "")
    body_md = doc.get("body_md", "")[:4000]  # 限制正文长度
    tags = ", ".join(doc.get("tags", []))

    system_prompt = (
        "你是这篇博客文章的 AI 阅读助手。你叫做「Roo 助手」。\n"
        "你的任务是基于以下文章内容回答用户的问题。\n"
        "要求：\n"
        "1. 回答要基于文章内容，准确且有帮助\n"
        "2. 如果问题超出文章范围，礼貌说明并建议用户去搜索更多内容\n"
        "3. 用中文回答，语言简洁易懂\n"
        "4. 如果用户问的是技术概念，可以用更通俗的方式解释\n\n"
        f"文章标题: {title}\n"
        f"文章标签: {tags}\n"
        f"文章内容:\n{body_md}\n"
    )

    messages = [{"role": "system", "content": system_prompt}]

    # 如果有历史记录，加入上下文
    if history:
        for msg in history[-6:]:  # 只保留最近6条
            if msg.get("role") in ("user", "assistant"):
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

    messages.append({"role": "user", "content": user_message})
    return messages


def ai_chat_stream(
    conn: sqlite3.Connection,
    content_type: str,
    slug: str,
    message: str,
    history: list[dict] | None = None,
) -> Generator[str, None, None]:
    """AI 阅读助手流式聊天。"""
    doc = _get_content_for_chat(conn, content_type, slug)
    if not doc:
        yield json.dumps({
            "type": "error",
            "content": f"未找到该{content_type}内容",
        })
        return

    try:
        messages = build_chat_messages(doc, message, history)
        stream = _llm_request(
            messages,
            temperature=0.7,
            max_tokens=1024,
            stream=True,
        )

        for token in stream:
            yield json.dumps({"type": "token", "content": token})

        yield json.dumps({"type": "done"})

    except RuntimeError as e:
        yield json.dumps({"type": "error", "content": str(e)})
    except Exception as e:
        yield json.dumps({"type": "error", "content": f"AI 服务请求失败: {e}"})


# ═══════════════════════════════════════════════════════════
# 3. AI 内容推荐
# ═══════════════════════════════════════════════════════════

def _find_related_by_tags(
    conn: sqlite3.Connection,
    current_type: str,
    current_slug: str,
    tags: list[str],
    exclude_slugs: set[str],
) -> list[dict]:
    """根据标签查找相关文章。"""
    related: list[dict] = []
    seen_slugs: set[str] = set(exclude_slugs)

    if current_type == "note":
        slugs = store.list_note_slugs_by_date(conn)
        getter = store.get_note
        type_name = "note"
    else:
        slugs = store.list_project_slugs_by_date(conn)
        getter = store.get_project
        type_name = "project"

    for slug in slugs:
        if slug in seen_slugs:
            continue
        doc = getter(conn, slug)
        if not doc:
            continue
        doc_tags = set(t.lower() for t in (doc.get("tags") or []))
        current_tags_lower = set(t.lower() for t in tags)
        match_count = len(doc_tags & current_tags_lower)
        if match_count > 0:
            related.append({
                "type": type_name,
                "slug": doc["slug"],
                "title": doc.get("title", ""),
                "summary": doc.get("summary", ""),
                "tags": doc.get("tags", []),
                "match_count": match_count,
            })
            seen_slugs.add(slug)

    # 按标签匹配数量降序
    related.sort(key=lambda x: x["match_count"], reverse=True)
    return related


def _generate_ai_reason(
    current_title: str, recommended_title: str, ai_enabled: bool
) -> str:
    """生成 AI 推荐理由。"""
    if not ai_enabled:
        return ""

    prompt = (
        "用一句话（15字内）解释为什么推荐这篇文章。\n"
        f"当前文章: {current_title}\n"
        f"推荐文章: {recommended_title}\n"
        "推荐理由:"
    )
    try:
        result = _llm_request(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=60,
        )
        return result["content"].strip()
    except Exception:
        return ""


def get_recommendations(
    conn: sqlite3.Connection,
    content_type: str,
    slug: str,
    limit: int = 3,
) -> list[dict]:
    """获取相关文章推荐。"""
    if content_type == "note":
        doc = store.get_note(conn, slug)
    else:
        doc = store.get_project(conn, slug)

    if not doc:
        return []

    tags = doc.get("tags", [])
    if not tags:
        return []

    related = _find_related_by_tags(
        conn, content_type, slug, tags, exclude_slugs={slug}
    )

    # 取前 limit 条，添加 AI 推荐理由
    results = []
    for item in related[:limit]:
        reason = _generate_ai_reason(
            doc.get("title", ""), item["title"], AI_ENABLED
        )
        item["ai_reason"] = reason
        results.append(item)

    return results


# ═══════════════════════════════════════════════════════════
# 4. AI 自动标签 & 摘要生成
# ═══════════════════════════════════════════════════════════

def auto_generate_tags(title: str, body: str) -> list[str]:
    """AI 自动生成标签。"""
    if not AI_ENABLED:
        return []

    # 检查缓存
    cache_key = f"{AI_TAGS_CACHE_PREFIX}{hash(title + body[:200])}"
    # 不在同步阶段写库缓存，避免与 content_sync 事务交织

    prompt = (
        "请根据文章标题和内容，生成3-5个中文标签，用逗号分隔。\n"
        "只输出标签，不要多余文字。\n"
        "要求：标签要准确反映文章的技术领域和核心主题。\n\n"
        f"标题: {title}\n"
        f"内容:\n{body[:800]}\n"
    )
    try:
        result = _llm_request(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=100,
        )
        content = result["content"].strip()
        tags = [t.strip() for t in content.split(",") if t.strip()]
        return tags[:6]  # 最多6个
    except Exception:
        return []


def auto_generate_summary(title: str, body: str) -> str:
    """AI 自动生成摘要。"""
    if not AI_ENABLED:
        return ""

    prompt = (
        "请为以下文章生成一段简洁的摘要（30-60字），"
        "概括文章的核心内容和价值。\n\n"
        f"标题: {title}\n"
        f"内容:\n{body[:1000]}\n\n"
        "摘要:"
    )
    try:
        result = _llm_request(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150,
        )
        return result["content"].strip()
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════
# 5. 健康检查
# ═══════════════════════════════════════════════════════════

def ai_status() -> dict:
    """返回 AI 服务状态。"""
    return {
        "enabled": AI_ENABLED,
        "model": LLM_MODEL,
        "api_url": _normalize_api_url(LLM_API_URL),
        "configured": bool(LLM_API_KEY),
    }
