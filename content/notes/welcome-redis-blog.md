---
title: 用 SQLite 做个人博客存储
slug: welcome-redis-blog
date: 2026-05-01
tags:
  - SQLite
  - Flask
  - Docker
summary: 启动时把 Markdown 同步进 SQLite，页面读库；单文件、少依赖，适合个人站点。
---

## 思路

- **权威数据源**：仓库里的 `content/notes/*.md` 与 `content/projects/*.md`（方便 Git 管理）。
- **运行期读取**：应用启动后把解析结果写入 **SQLite**（`notes` / `projects` 表），请求阶段查库即可。
- **清理**：磁盘上删掉的文档，会在下次同步时从库里移除对应行。

## 本地开发

```bash
docker compose up --build
```

容器内默认 `SQLITE_PATH=/app/data/blog.db`（Compose 挂了数据卷）。改一篇 Markdown 后 **重启 web 容器** 即可重新同步。

## 代码块示例

```python
import sqlite3

conn = sqlite3.connect("data/blog.db")
conn.execute("SELECT 1").fetchone()
```
