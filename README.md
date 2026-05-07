# 个人 AI 博客

Flask + SQLite + Docker 的极简个人博客，集成了 AI 智能搜索、阅读助手、内容推荐、智慧箴言等功能。

## 项目结构

```
个人博客/
│
├── blog/                          # Flask 应用核心（所有 Python 代码）
│   ├── main.py                    # ★ 应用入口 — app factory，注册路由，注入全局变量
│   ├── config.py                  # ★ 全局配置 — 环境变量 + HTTP 会话 + 回退数据
│   ├── db.py                      # 数据库启动 — 打开 SQLite 连接的入口
│   │
│   ├── sqlite_store.py            # 数据访问层 — 建表/CRUD/查询/迁移
│   ├── content_sync.py            # 内容同步 — 解析 content/ 下 Markdown 写入 SQLite
│   ├── github_sync.py             # GitHub 同步 — 通过 API 拉取远程仓库的 Markdown
│   │
│   ├── ai_service.py              # AI 服务层 — 智能搜索/阅读助手/推荐/自动标签
│   ├── wisdom_service.py          # 箴言服务 — LLM 生成箴言 + 调用生图 API
│   │
│   ├── routes_content.py          # SSR 路由 — 首页/笔记列表/笔记详情/项目/箴言页/AI搜索页
│   ├── routes_ai.py               # AI API — 搜索/聊天(SSE流式)/推荐/状态
│   ├── routes_wisdom.py           # 箴言 API — LLM箴言/生图/下载/图片代理
│   ├── routes_system.py           # 系统路由 — 健康检查 + LLM 状态
│   │
│   ├── static/                    # 静态资源
│   │   ├── css/
│   │   │   ├── design-system.css  # ★ 设计系统变量 — 颜色/字体/阴影/工具类
│   │   │   ├── base.css           # 基础导入 — @import design-system.css
│   │   │   ├── layout.css         # 布局 — 左侧边栏/阅读进度条/页脚/响应式
│   │   │   ├── components.css     # 组件 — 卡片/文章/标签/按钮/Hero
│   │   │   ├── home.css           # 首页 — Hero区/统计条/关于卡片
│   │   │   ├── timeline.css       # 时间线 — 垂直线/圆点标记/年度分隔
│   │   │   ├── toc.css            # 文章目录 — 右侧固定面板
│   │   │   ├── chat-widget.css    # AI聊天组件 — 浮动按钮/面板/消息气泡
│   │   │   ├── ai-search.css      # AI搜索页 — 搜索框/结果卡片
│   │   │   ├── wisdom.css         # 箴言页 — 全屏卡片/按钮组
│   │   │   └── utilities.css      # 工具 — 空状态/辅助类
│   │   │
│   │   └── js/
│   │       ├── theme.js           # 主题切换 — 默认暗色/localStorage持久化
│   │       ├── progress.js        # 阅读进度条 — 滚动时更新顶部进度
│   │       ├── back-to-top.js     # 回到顶部 — 400px后显示/平滑滚动
│   │       ├── chat-widget.js     # AI聊天 — SSE流式读取/消息历史
│   │       ├── ai-search.js       # AI搜索 — 查询/渲染结果
│   │       └── wisdom.js          # 箴言页 — 本地箴言库/API调用/海报生成
│   │
│   └── templates/                 # Jinja2 模板
│       ├── base.html              # ★ 基础布局 — 左侧边栏+移动顶栏+页脚结构
│       ├── home.html              # 首页 — Hero/统计/笔记卡片/项目卡片
│       ├── notes_list.html        # 笔记列表 — 时间线布局
│       ├── projects_list.html     # 项目列表 — 时间线布局
│       ├── note_detail.html       # 笔记详情 — 文章+目录+推荐+AI聊天
│       ├── project_detail.html    # 项目详情 — 文章+目录+推荐+AI聊天
│       ├── ai_search.html         # AI搜索 — 搜索框+结果区
│       ├── wisdom.html            # 箴言页 — 图片+箴言+按钮组
│       ├── macros/                # 可复用宏
│       │   ├── article.html       # 文章头/正文/返回链接
│       │   ├── cards.html         # 卡片网格/单卡片
│       │   ├── tags.html          # 标签列表
│       │   └── timeline.html      # 时间线条目
│       └── components/            # 可复用组件
│           ├── ai_chat_widget.html    # AI聊天浮动组件
│           └── recommend_section.html # 推荐区域
│
├── content/                       # Markdown 内容（你写文章的地方）
│   ├── notes/                     # 学习笔记 — *.md → /notes/<slug>
│   └── projects/                  # 项目介绍 — *.md → /projects/<slug>
│
├── deploy/                        # 部署配置
│   ├── nginx.conf                 # Docker Compose 内 Nginx 反代
│   ├── nginx.prod.conf            # 服务器已有 Nginx 的反代配置
│   ├── nginx.ssl.example.conf     # HTTPS 配置示例
│   ├── DEPLOY_GUIDE.md            # 宝塔面板部署简版指南
│   └── 完整部署教程.md             # ★ 从零到 HTTPS 的完整部署教程
│
├── docs/                          # 项目文档
│   ├── AI_BLOG_PLAN.md            # 技术架构文档
│   └── 使用与部署教程.md           # 使用说明
│
├── data/                          # SQLite 数据库文件存放（不入 git）
│
├── .env.example                   # 环境变量模板 — 复制为 .env 填入密钥
├── .env                           # 实际密钥配置（不入 git）
├── .gitignore                     # Git 忽略规则
├── .dockerignore                  # Docker 构建忽略
├── Dockerfile                     # 容器镜像构建脚本
├── docker-compose.yml             # 本地开发 — Flask + Nginx 双容器
├── docker-compose.prod.yml        # 生产部署 — 仅 Flask 容器
├── requirements.txt               # Python 依赖包
└── README.md                      # 本文件
```

## 数据流向

```
你写 Markdown                    用户访问网站
     │                                ▲
     ▼                                │
content/notes/*.md  ──┐           Jinja2 模板渲染
content/projects/*.md  │               ▲
                       │               │
GitHub 远程仓库 *.md ──┤           SQLite 查询
                       │               ▲
                       ▼               │
              content_sync.py      routes_*.py
              github_sync.py            │
                       │               │
                       ▼               │
                  SQLite 数据库 ────────┘
```

## 页面路由

| URL | 页面 | 功能 |
|-----|------|------|
| `/` | 首页 | Hero + 关于 + 最新笔记/项目卡片 |
| `/notes` | 笔记列表 | 时间线布局 |
| `/notes/<slug>` | 笔记详情 | 文章 + 目录 + AI推荐 + 阅读助手 |
| `/projects` | 项目列表 | 时间线布局 |
| `/projects/<slug>` | 项目详情 | 文章 + 目录 + AI推荐 + 阅读助手 |
| `/ai/search` | AI 搜索 | 自然语言搜索 |
| `/playground/wisdom` | 智慧箴言 | AI 箴言 + 背景图 + 海报下载 |

## API 路由

| 方法 | URL | 说明 |
|------|-----|------|
| POST | `/api/ai/search` | AI 智能搜索 |
| POST | `/api/ai/chat` | AI 阅读助手 SSE 流式聊天 |
| POST | `/api/ai/recommend` | AI 内容推荐 |
| GET | `/api/ai/status` | AI 服务状态 |
| GET | `/api/llm/wisdom` | AI 生成箴言 |
| GET | `/api/llm/status` | LLM/生图配置状态 |
| GET | `/api/wisdom/background` | 背景图描述 |
| GET | `/api/wisdom/render-image` | 生图 API 调用 |
| GET | `/api/wisdom/download-image` | 下载外部图片 |
| GET | `/api/wisdom/image-proxy` | 图片代理 |
| GET | `/healthz` | 健康检查 |

## 快速启动

```bash
# 1. 复制环境变量模板
cp .env.example .env
# 编辑 .env 填入你的 API 密钥

# 2. 启动
docker compose up --build

# 3. 访问 http://localhost
```

## 技术栈

| 层 | 技术 |
|----|------|
| Web 框架 | Flask 3.x + Jinja2 SSR |
| 数据库 | SQLite (WAL 模式) |
| 内容管理 | Markdown + YAML Front Matter |
| 容器化 | Docker + Docker Compose |
| AI 文本 | OpenAI 兼容 API（DeepSeek via SiliconFlow） |
| AI 生图 | OpenAI 兼容 API（doubao-seedream via 火山引擎） |
| 前端 | 原生 CSS 变量 + 原生 JS，无框架依赖 |
| 部署 | Nginx 反代 + Let's Encrypt SSL |
