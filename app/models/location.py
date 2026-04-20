from app.extensions import db

class Location(db.Model):
    __tablename__ = 'locations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    city = db.Column(db.String, default='Москва')
    country = db.Column(db.String, default='Россия')
    description = db.Column(db.String, nullable=True)

    games = db.relationship('Game', back_populates='location', lazy='dynamic')

    __table_args__ = (db.UniqueConstraint('lat', 'lon', name='_lat_lon_uc'),)

    def __repr__(self):
        return f'<Location {self.id} {self.city} ({self.lat}, {self.lon})>'