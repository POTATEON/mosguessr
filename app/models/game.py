import datetime
from app.extensions import db

class Game(db.Model):
    __tablename__ = 'games'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    user_guess_lat = db.Column(db.Float)
    user_guess_lon = db.Column(db.Float)
    distance = db.Column(db.Float)  # в метрах
    score = db.Column(db.Integer)
    is_surprise = db.Column(db.Boolean, default=False)
    actual_city = db.Column(db.String, default='Москва')
    played_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', back_populates='games')
    location = db.relationship('Location', back_populates='games')

    def __repr__(self):
        return f'<Game {self.id} score={self.score}>'