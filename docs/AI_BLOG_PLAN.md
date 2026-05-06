# 个人 AI 博客 — 技术架构规划

## 一、现状分析

### 现有基础设施
| 组件 | 技术栈 | 说明 |
|------|--------|------|
| Web 框架 | Flask | Blueprint 模块化路由 |
| 存储层 | SQLite + Markdown | 启动时从 Markdown 同步到 SQLite |
| 容器化 | Docker + Docker Compose | web 服务 + 数据卷 |
| AI 引擎 | OpenAI 兼容 API | LLM（DeepSeek）+ 生图（doubao-seedream） |
| 前端 | Jinja2 模板 + CSS/JS | 服务端渲染，深色模式支持 |

### 现有页面
- 首页（Hero + 关于 + 笔记/项目概览）
- 笔记列表 / 详情（含 AI 推荐 + 阅读助手聊天）
- 项目列表 / 详情
- 智慧箴言（AI 生成 + 图片 + 海报下载）
- AI 智能搜索

### 已实现的 AI 能力
- AI 智能搜索（关键词提取 + 本地匹配 + AI 解读）
- AI 阅读助手（SSE 流式聊天，基于文章内容）
- AI 内容推荐（标签匹配 + AI 推荐理由）
- AI 自动标签和摘要生成
- AI 箴言 + 生图（9:16 竖屏背景图）
- 海报 Canvas 合成下载

### 代码架构

```
blog/
├── main.py              # app factory (30行)
├── config.py            # 环境变量 & 常量集中管理
├── db.py                # 数据库启动
├── content_sync.py      # Markdown → SQLite 同步
├── sqlite_store.py      # 数据访问层
├── ai_service.py        # AI 服务层 (搜索/聊天/推荐/标签)
├── wisdom_service.py    # 箴言 & 生图服务
├── routes_content.py    # SSR 页面路由
├── routes_ai.py         # AI API 路由
├── routes_wisdom.py     # 箴言 API 路由
├── routes_system.py     # 健康检查路由
├── static/
│   ├── css/             # 8个CSS文件 (base/layout/components/utilities/home/chat-widget/ai-search/wisdom)
│   └── js/              # 4个JS文件 (theme/chat-widget/ai-search/wisdom)
└── templates/
    ├── macros/          # Jinja2 宏 (cards/tags/article)
    └── components/      # 可复用组件 (chat_widget/recommend_section)
```

---

## 二、AI 博客功能设计

### 核心功能矩阵
| 功能 | 技术 | 价值 |
|------|------|------|
| AI 智能搜索 | LLM + SQLite | 自然语言搜索学习笔记 |
| AI 阅读助手 | LLM + SSE | 边读边问，理解内容 |
| AI 内容推荐 | LLM + 标签 | 发现关联知识 |
| AI 自动标签 | LLM | 无需手动打标签 |
| AI 摘要 | LLM | 快速了解文章要点 |
| 智慧箴言 | LLM + 生图 | AI 哲理短句 + 配图 |

### API 一览

| 方法 | URL | 说明 |
|------|-----|------|
| POST | `/api/ai/search` | AI 智能搜索 |
| POST | `/api/ai/chat` | AI 阅读助手 SSE 流式 |
| POST | `/api/ai/recommend` | AI 内容推荐 |
| GET | `/api/ai/status` | AI 服务状态 |
| GET | `/api/llm/wisdom` | AI 生成箴言 |
| GET | `/api/llm/status` | LLM/生图配置状态 |
| GET | `/api/wisdom/background` | 背景图 URL |
| GET | `/api/wisdom/render-image` | 渲染生图 |
| GET | `/api/wisdom/download-image` | 下载背景图 |
| GET | `/api/wisdom/image-proxy` | 图片代理 |
| GET | `/healthz` | 健康检查 |

---

## 三、部署

### 本地开发
```bash
docker compose up --build
# 访问 http://localhost
```

### 生产部署（已有 Nginx 的服务器）
```bash
docker compose -f docker-compose.prod.yml up -d --build
# 配合服务器 Nginx 反代到 127.0.0.1:8080
```

环境变量（`.env`）：
```
LLM_API_URL=https://api.siliconflow.cn/v1
LLM_API_KEY=your_key
LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash
IMAGE_API_KEY=your_key
IMAGE_API_BASE=https://ark.cn-beijing.volces.com/api/v3
IMAGE_MODEL=doubao-seedream-4-5-251128
```

---

## 四、设计系统

- **配色**: 靛蓝 `#4f6ef7`，浅色/深色双主题
- **字体**: Inter (UI) + Noto Sans SC (中文)
- **主题切换**: `[data-theme="dark"]`，localStorage 持久化
- **CSS 变量**: 所有颜色/阴影/圆角统一管理
