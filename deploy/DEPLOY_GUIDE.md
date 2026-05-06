# 部署指南 — 宝塔面板服务器

你的服务器已有 Nginx（宝塔管理），所以只需用 Docker 跑 Flask，
再用宝塔的 Nginx 做反代。不会和现有服务冲突。

---

## 第 1 步：安装 Docker（如果还没有）

SSH 连接到 117.72.23.59，运行：

```bash
curl -fsSL https://get.docker.com | bash
systemctl enable docker
systemctl start docker
docker --version
```

如果提示 `docker compose` 不可用，再装插件：

```bash
docker compose version 2>/dev/null || docker plugin install compose
```

或者直接装 Docker Compose 独立版：

```bash
apt install docker-compose-plugin -y
```

---

## 第 2 步：上传项目到服务器

在服务器上创建目录并上传项目（选一种方式）：

**方式 A — Git 克隆（推荐）**

```bash
cd /www
git clone <你的仓库地址> blog
```

**方式 B — 宝塔文件管理器**
- 打开宝塔面板 → 文件
- 上传项目 zip 包到 `/www/blog/`
- 解压

---

## 第 3 步：检查 .env 配置

确保 `.env` 文件在项目根目录存在，包含 API 密钥：

```bash
cd /www/blog
cat .env
```

如果缺失，在宝塔面板文件管理器中创建，内容参考你本地的 `.env`。

**安全提醒**：`.env` 包含 API 密钥，不要提交到 Git。

---

## 第 4 步：启动 Flask 容器

```bash
cd /www/blog

# 用生产配置构建并启动（仅 web 容器，不使用 docker-compose.yml 里的 nginx）
docker compose -f docker-compose.prod.yml up -d --build

# 确认运行正常
docker compose -f docker-compose.prod.yml ps
curl http://127.0.0.1:8080/healthz
```

应该返回 `{"ok": true, "sqlite": true}`。

---

## 第 5 步：配置宝塔 Nginx 反代

1. 打开 **宝塔面板** → **网站** → 点击你的站点 (uniapp.love)
2. 点击 **配置文件**
3. 将 `location /` 替换为以下内容：

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection "";

    # AI 阅读助手 SSE 流式输出
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
}
```

4. 点击 **保存**
5. 点击 **重载配置**

---

## 第 6 步：配置 SSL (HTTPS)

宝塔面板 → 网站 → 你的站点 → **SSL** → **Let's Encrypt**

选择 `uniapp.love`，申请证书。宝塔会自动续期。

---

## 第 7 步：验证

浏览器访问：

- `https://uniapp.love` → 首页
- `https://uniapp.love/notes` → 笔记列表
- `https://uniapp.love/ai/search` → AI 搜索
- `https://uniapp.love/healthz` → 健康检查

---

## 日常维护

**更新代码后重启：**

```bash
cd /www/blog
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

**查看日志：**

```bash
docker compose -f docker-compose.prod.yml logs -f --tail=100
```

**数据库备份：**

```bash
# SQLite 文件在 Docker 数据卷中
docker compose -f docker-compose.prod.yml exec web cp /app/data/blog.db /app/data/blog.db.bak
```

或者在宝塔面板中定期备份 `/var/lib/docker/volumes/` 下的 `sqlite-data` 卷。

---

## 端口说明

| 组件 | 端口 | 对外 |
|------|------|------|
| 宝塔 Nginx | 80/443 | ✅ 公网 |
| Flask (Docker) | 127.0.0.1:8080 | ❌ 仅本地 |
