import datetime
import sqlalchemy as sa
import sqlalchemy.orm as orm
from werkzeug.security import generate_password_hash, check_password_hash
from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    """Модель пользователя (как в уроке WEB 3)"""
    __tablename__ = 'users'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String, nullable=True)
    email = sa.Column(sa.String, index=True, unique=True, nullable=True)
    hashed_password = sa.Column(sa.String, nullable=True)
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)

    # Связь с играми
    games = orm.relationship("Game", back_populates='user')

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    # Методы для Flask-Login (если будем использовать)
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f'<User> {self.id} {self.name} {self.email}'


class Location(SqlAlchemyBase):
    """Модель локации (панорамы)"""
    __tablename__ = 'locations'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    lat = sa.Column(sa.Float, nullable=False)
    lon = sa.Column(sa.Float, nullable=False)
    city = sa.Column(sa.String, default='Москва')
    country = sa.Column(sa.String, default='Россия')
    description = sa.Column(sa.String, nullable=True)

    # Связь с играми
    games = orm.relationship("Game", back_populates='location')

    # Уникальность координат
    __table_args__ = (sa.UniqueConstraint('lat', 'lon', name='_lat_lon_uc'),)

    def __repr__(self):
        return f'<Location> {self.id} {self.city} ({self.lat}, {self.lon})'


class Game(SqlAlchemyBase):
    """Модель игры (раунда)"""
    __tablename__ = 'games'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=True)
    location_id = sa.Column(sa.Integer, sa.ForeignKey("locations.id"))
    user_guess_lat = sa.Column(sa.Float)
    user_guess_lon = sa.Column(sa.Float)
    distance = sa.Column(sa.Float)  # в метрах
    score = sa.Column(sa.Integer)
    is_surprise = sa.Column(sa.Boolean, default=False)
    actual_city = sa.Column(sa.String, default='Москва')
    played_at = sa.Column(sa.DateTime, default=datetime.datetime.now)

    # Связи
    user = orm.relationship("User", back_populates='games')
    location = orm.relationship("Location", back_populates='games')

    def __repr__(self):
        return f'<Game> {self.id} score={self.score} city={self.actual_city}'