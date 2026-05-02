---
title: "AI 博客系统"
date: 2026-05-01
tags: ["Python", "Flask", "AI", "SQLite", "Docker"]
repo: "https://github.com/yourname/ai-blog"
summary: "一个集成 AI 功能的个人博客系统，支持智能搜索、阅读助手和内容推荐。"
---

# AI 博客系统

一个基于 Flask + SQLite 的个人博客，集成了多种 AI 功能。

## 项目特点

- **AI 智能搜索** — 自然语言搜索笔记和项目
- **AI 阅读助手** — 边读边问，基于文章内容回答
- **AI 内容推荐** — 智能推荐相关内容
- **AI 自动标签** — 自动生成文章标签和摘要
- **智慧箴言** — AI 生成带配图的精美箴言
- **Markdown 驱动** — 内容用 Markdown 管理，简单直观
- **Docker 部署** — 一键启动，无需复杂配置

## 技术架构

```
浏览器 → Flask → SQLite (存储)
            ↓
         LLM API (DeepSeek/OpenAI)
```

## 核心模块

| 文件 | 用途 |
|------|------|
| `blog/main.py` | Flask 应用主入口 |
| `blog/ai_service.py` | AI 服务层（搜索、聊天、推荐） |
| `blog/content_sync.py` | Markdown 同步到 SQLite |
| `blog/sqlite_store.py` | SQLite 数据操作 |

## 快速开始

1. 克隆项目
2. 配置 `.env` 文件
3. 运行 `docker compose up --build`
4. 访问 `http://localhost:8080`

## 环境变量

```env
LLM_API_URL=https://api.deepseek.com/chat/completions
LLM_API_KEY=sk-xxxxxxxx
LLM_MODEL=deepseek-chat
```

## 截图

- 首页展示笔记和项目
- AI 搜索页面
- 文章详情页（含 AI 助手）
- 智慧箴言页面
