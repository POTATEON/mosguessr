import datetime
from app.extensions import db


class Duel(db.Model):
    __tablename__ = 'duels'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    player1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='waiting')  # waiting, in_progress, finished
    current_round = db.Column(db.Integer, default=1)
    round_start_time = db.Column(db.DateTime)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    lobby_id = db.Column(db.String(20), nullable=True)  # NULL = обычная очередь
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    finished_at = db.Column(db.DateTime)

    # Связи
    player1 = db.relationship('User', foreign_keys=[player1_id])
    player2 = db.relationship('User', foreign_keys=[player2_id])
    location = db.relationship('Location')
    guesses = db.relationship('DuelGuess', back_populates='duel', lazy='dynamic')

    def get_player_score(self, user_id):
        """Сумма очков игрока за все раунды"""
        return sum(g.score or 0 for g in self.guesses.filter_by(user_id=user_id).all())

    def get_round_guesses(self, round_num):
        """Получить ответы обоих игроков за раунд"""
        return self.guesses.filter_by(round_number=round_num).all()

    def both_answered(self, round_num):
        """Проверить, ответили ли оба в раунде"""
        return self.guesses.filter_by(round_number=round_num).count() == 2


class DuelGuess(db.Model):
    __tablename__ = 'duel_guesses'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    duel_id = db.Column(db.Integer, db.ForeignKey('duels.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    guess_lat = db.Column(db.Float)
    guess_lon = db.Column(db.Float)
    distance = db.Column(db.Float)
    score = db.Column(db.Integer)
    time_taken = db.Column(db.Float)  # секунд до ответа
    submitted_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    duel = db.relationship('Duel', back_populates='guesses')
    user = db.relationship('User')