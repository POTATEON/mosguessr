import datetime
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.avatar import generate_avatar_svg, process_uploaded_avatar, delete_old_avatar
from werkzeug.utils import secure_filename

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=True)
    email = db.Column(db.String, index=True, unique=True, nullable=True)
    hashed_password = db.Column(db.String, nullable=True)
    created_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    games = db.relationship('Game', back_populates='user', lazy='dynamic')
    avatar_type = db.Column(db.String(20), default='svg')  # 'svg', 'upload'
    avatar_url = db.Column(db.String(500), nullable=True)
    avatar_updated_at = db.Column(db.DateTime)

    def get_avatar_svg(self, size=200):
        """Получить SVG аватар"""
        return generate_avatar_svg(self.name or "A", size)

    def set_avatar(self, file):
        """Установить загруженный аватар"""
        if not file:
            return False

        # Удаляем старый аватар если был загруженный
        if self.avatar_type == 'upload' and self.avatar_url:
            delete_old_avatar(self.avatar_url)

        # Получаем имя файла
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename or 'avatar.jpg')

        # Читаем данные файла
        file_data = file.read()

        # Обрабатываем новый файл
        url = process_uploaded_avatar(file_data, self.id, filename)

        if url:
            self.avatar_url = url
            self.avatar_type = 'upload'
            self.avatar_updated_at = datetime.datetime.utcnow()
            return True

        return False

    def set_avatar_to_svg(self):
        """Переключить на SVG аватар"""
        if self.avatar_type == 'upload' and self.avatar_url:
            delete_old_avatar(self.avatar_url)

        self.avatar_type = 'svg'
        self.avatar_url = None

    def get_avatar_url(self, size=200):
        """Получить URL аватара с учетом типа"""
        if self.avatar_type == 'upload' and self.avatar_url:
            return self.avatar_url
        else:
            # Для SVG возвращаем data URI
            svg = self.get_avatar_svg(size)
            import base64
            b64 = base64.b64encode(svg.encode()).decode()
            return f"data:image/svg+xml;base64,{b64}"

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    def __repr__(self):
        return f'<User {self.id} {self.name}>'