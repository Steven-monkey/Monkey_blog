"""个人博客 —— Flask 应用入口（app factory 模式）。

启动流程：
1. create_app() 创建 Flask 实例，注册 4 个 Blueprint
2. context_processor 注入 author_name / now 到所有模板
3. bootstrap_db() 同步本地 Markdown 和 GitHub 笔记到 SQLite
"""

import logging
from datetime import datetime

from flask import Flask

from blog.config import AUTHOR_NAME, HOST, PORT
from blog.db import bootstrap_db
from blog.routes_content import content_bp
from blog.routes_ai import ai_bp
from blog.routes_wisdom import wisdom_bp
from blog.routes_system import system_bp

logging.basicConfig(level=logging.INFO)


def create_app():
    """Flask app factory —— 注册 Blueprint 和全局模板变量。"""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.context_processor
    def inject_globals():
        """所有模板中可直接使用 {{ author_name }} 和 {{ now }}。"""
        return {
            "author_name": AUTHOR_NAME,
            "now": datetime.now(),
        }

    app.register_blueprint(content_bp)   # SSR 页面路由
    app.register_blueprint(ai_bp)        # AI API
    app.register_blueprint(wisdom_bp)    # 箴言 API
    app.register_blueprint(system_bp)    # 健康检查

    return app


app = create_app()
bootstrap_db()

if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
