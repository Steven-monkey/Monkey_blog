# 部署相关文件

- **`nginx.conf`**：`docker-compose` 里 Nginx 容器的站点配置，反向代理到内部 `web:8080`。
- **`nginx.ssl.example.conf`**：若要在本机 Nginx 上配置 HTTPS，可参考复制后改域名与证书路径（与 Compose 内 Nginx 二选一即可）。
