from flask import Flask
from app.config import Config
from app.extensions import db, migrate
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db)

    # Регистрация blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.game import bp as game_bp
    app.register_blueprint(game_bp)

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Главная страница
    from flask import render_template
    from app.utils.helpers import get_current_user

    @app.route('/')
    def index():
        user = get_current_user()
        return render_template('index.html', user=user)

    from flask import Response

    @app.route('/sw.js')
    def service_worker():
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        sw_path = os.path.join(static_dir, 'sw.js')

        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return Response(content, mimetype='application/javascript')
    return app