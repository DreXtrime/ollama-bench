from flask import Flask, render_template
from .database import init_db


def create_app():
    app = Flask(__name__)

    init_db()

    from .routes.models import models_bp
    from .routes.tests import tests_bp
    from .routes.runs import runs_bp

    app.register_blueprint(models_bp)
    app.register_blueprint(tests_bp)
    app.register_blueprint(runs_bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    return app
