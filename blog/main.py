"""个人博客 — Flask 应用入口。"""

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
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.context_processor
    def inject_globals():
        return {
            "author_name": AUTHOR_NAME,
            "now": datetime.now(),
        }

    app.register_blueprint(content_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(wisdom_bp)
    app.register_blueprint(system_bp)
    return app


app = create_app()
bootstrap_db()

if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
