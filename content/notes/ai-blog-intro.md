---
title: "AI 博客功能介绍"
date: 2026-05-01
tags: ["AI", "博客", "Python", "Flask"]
summary: "介绍个人博客中集成的 AI 功能，包括智能搜索、阅读助手和内容推荐。"
---

# AI 博客功能介绍

这个博客集成了多种 AI 功能，让学习笔记和项目展示更加智能化。

## 功能概览

### 1. AI 智能搜索

在导航栏点击 **🔍 AI 搜索**，可以用自然语言搜索你的所有笔记和项目。

例如：
- "Docker 部署 Flask 的方法"
- "SQLite 与 Flask 集成"
- "Python 异步编程"

AI 会自动提取关键词，并在搜索结果中给出智能解读。

### 2. AI 阅读助手

在阅读任何笔记或项目时，右下角会出现 **🤖 AI 阅读助手** 按钮。

你可以问它：
- "这篇文章的核心观点是什么？"
- "能解释一下这个概念吗？"
- "这篇文章和之前的内容有什么联系？"

AI 会基于当前文章内容回答你的问题。

### 3. AI 内容推荐

每篇文章底部会显示 **"你可能也喜欢"**，AI 会根据标签匹配和语义相似度推荐相关内容。

### 4. 智慧箴言

原有的 AI 箴言功能保留，可以生成带配图的精美箴言。

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | Flask |
| 存储 | SQLite |
| AI 引擎 | DeepSeek / OpenAI 兼容 API |
| 容器化 | Docker + Docker Compose |
| 内容管理 | Markdown + Front Matter |

## 部署方式

```bash
docker compose up --build
```

需要配置环境变量：

```
LLM_API_URL=https://api.deepseek.com/chat/completions
LLM_API_KEY=your_api_key
LLM_MODEL=deepseek-chat
```

## 内容管理

所有内容都放在 `content/` 目录下：

- `content/notes/` — 学习笔记
- `content/projects/` — 项目展示

使用 Markdown 格式，支持 YAML Front Matter：

```markdown
---
title: "文章标题"
date: 2026-05-01
tags: ["Python", "Docker"]
summary: "文章摘要（可选，AI 可自动生成）"
---

正文内容...
```

启动时会自动同步到 SQLite，无需手动操作数据库。
