from flask import Flask, Response
from app.config import Config
from app.extensions import db, migrate, socketio
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*")

    # Регистрация blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.game import bp as game_bp
    app.register_blueprint(game_bp)

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from app.socketio import register_handlers
    register_handlers()

    # Создание таблиц, если их нет
    with app.app_context():
        from app.models.user import User
        from app.models.location import Location
        from app.models.game import Game
        from app.models.duel import Duel, DuelGuess  # ← добавить импорт
        db.create_all()  # ← создаст все недостающие таблицы

    # Главная страница
    from flask import render_template
    from app.utils.helpers import get_current_user

    @app.route('/')
    def index():
        user = get_current_user()
        return render_template('index.html', user=user)

    @app.route('/duel_create.js')
    def duel_create():
        static_dir = os.path.join(os.path.dirname(__file__), 'static/js')
        sw_path = os.path.join(static_dir, 'duel_create.js')

        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return Response(content, mimetype='application/javascript')
    return app