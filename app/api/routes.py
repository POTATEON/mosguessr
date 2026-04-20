from flask import jsonify
from app.api import bp
from app.extensions import db
from app.models.game import Game
from app.models.user import User

@bp.route('/leaderboard')
def leaderboard():
    top_games = db.session.query(Game).order_by(Game.score.desc()).limit(20).all()
    result = []
    for g in top_games:
        result.append({
            'id': g.id,
            'score': g.score,
            'distance': g.distance,
            'city': g.actual_city,
            'user': g.user.name if g.user else 'Аноним',
            'played_at': g.played_at.isoformat()
        })
    return jsonify(result)

@bp.route('/stats/<int:user_id>')
def user_stats(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    games = user.games.order_by(Game.score.desc()).all()
    total_games = len(games)
    total_score = sum(g.score for g in games)
    avg_score = total_score / total_games if total_games > 0 else 0
    best_game = max(games, key=lambda g: g.score) if games else None

    return jsonify({
        'user_id': user.id,
        'name': user.name,
        'total_games': total_games,
        'total_score': total_score,
        'avg_score': round(avg_score, 2),
        'best_score': best_game.score if best_game else 0
    })