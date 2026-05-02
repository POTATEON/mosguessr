"""Логика классической дуэли"""
import datetime
from flask import current_app
from app.extensions import socketio, db
from app.models.duel import Duel, DuelGuess
from app.models.location import Location
from app.models.user import User
from app.utils.geo import get_random_city, calculate_score, haversine
from .state import (
    duel_rooms, active_lobbies, round_timers, next_round_ready,
    panorama_regeneration_count, panorama_regeneration_lock
)
from .helpers import (
    save_location, calculate_speed_bonus,
    get_duel_player_sids, send_to_duel_players, cancel_round_timer
)


def create_duel(player1, player2, lobby_id=None):
    duel = Duel(
        player1_id=player1['user_id'], player2_id=player2['user_id'],
        status='in_progress', current_round=1, lobby_id=lobby_id
    )
    db.session.add(duel)
    db.session.commit()

    duel_rooms[duel.id] = {player1['user_id']: player1['sid'], player2['user_id']: player2['sid']}

    if lobby_id and lobby_id in active_lobbies:
        active_lobbies[lobby_id]['duel'] = duel.id

    for player in [player1, player2]:
        opponent = player2 if player == player1 else player1
        socketio.emit('duel_found', {
            'duel_id': duel.id,
            'opponent_name': opponent['name'],
            'opponent_id': opponent['user_id'],
            'my_user_id': player['user_id']
        }, room=player['sid'])


def start_duel_round(duel_id):
    cancel_round_timer(duel_id)

    with panorama_regeneration_lock:
        panorama_regeneration_count.pop(duel_id, None)
        panorama_regeneration_count.pop(f"{duel_id}_time", None)

    duel = db.session.get(Duel, duel_id)
    if not duel or duel.status != 'in_progress':
        return

    search_lat, search_lon, city_name = get_random_city()
    location = save_location(search_lat, search_lon, city_name)

    duel.location_id = location.id
    duel.round_start_time = datetime.datetime.utcnow()
    db.session.commit()

    next_round_ready.pop(duel_id, None)

    round_data = {
        'duel_id': duel_id, 'round_number': duel.current_round,
        'search_lat': search_lat, 'search_lon': search_lon, 'city': city_name
    }
    send_to_duel_players(duel_id, 'start_round', round_data)

    round_timers[duel_id] = {'round': duel.current_round, 'started': datetime.datetime.utcnow()}

    app = current_app._get_current_object()
    socketio.start_background_task(_timer_task, app, duel_id, duel.current_round)


def _timer_task(app, duel_id, round_num):
    for _ in range(60):
        socketio.sleep(1)
        if duel_id not in round_timers or round_timers[duel_id].get('round') != round_num:
            return

    with app.app_context():
        _handle_round_timeout(duel_id, round_num)


def _handle_round_timeout(duel_id, round_num):
    cancel_round_timer(duel_id)

    duel = db.session.get(Duel, duel_id)
    if not duel or duel.status != 'in_progress' or duel.current_round != round_num:
        return

    existing = duel.get_round_guesses(round_num)
    answered_ids = {g.user_id for g in existing}

    for uid in [duel.player1_id, duel.player2_id]:
        if uid not in answered_ids:
            db.session.add(DuelGuess(
                duel_id=duel_id, user_id=uid, round_number=round_num,
                guess_lat=None, guess_lon=None, distance=None, score=0, time_taken=60.0
            ))

    db.session.commit()
    _send_round_results(duel_id)


def submit_guess(duel_id, user_id, guess_lat, guess_lon):
    duel = db.session.get(Duel, duel_id)
    if not duel or duel.status != 'in_progress':
        return False, 'Дуэль неактивна'

    if duel.round_start_time:
        elapsed = (datetime.datetime.utcnow() - duel.round_start_time).total_seconds()
        if elapsed > 60:
            return False, 'Время истекло'

    existing = DuelGuess.query.filter_by(duel_id=duel_id, user_id=user_id, round_number=duel.current_round).first()
    if existing:
        return False, 'Вы уже сделали ход'

    location = db.session.get(Location, duel.location_id)
    if not location:
        return False, 'Локация не найдена'

    if guess_lat is not None and guess_lon is not None:
        distance = haversine(guess_lat, guess_lon, location.lat, location.lon)
        distance_km = distance / 1000.0
    else:
        distance = None
        distance_km = None

    time_taken = (datetime.datetime.utcnow() - duel.round_start_time).total_seconds()
    base_score = calculate_score(distance_km, location.city != "Москва") if distance_km else 0
    score = base_score + calculate_speed_bonus(time_taken)

    db.session.add(DuelGuess(
        duel_id=duel_id, user_id=user_id, round_number=duel.current_round,
        guess_lat=guess_lat, guess_lon=guess_lon, distance=distance, score=score, time_taken=time_taken
    ))
    db.session.commit()

    if duel.guesses.filter_by(round_number=duel.current_round).count() >= 2:
        cancel_round_timer(duel_id)
        _send_round_results(duel_id)

    return True, None


def _send_round_results(duel_id):
    duel = db.session.get(Duel, duel_id)
    if not duel:
        return

    location = db.session.get(Location, duel.location_id)
    guesses = duel.get_round_guesses(duel.current_round)

    players_data = []
    for g in guesses:
        player = db.session.get(User, g.user_id) if g.user_id else None
        players_data.append({
            'user_id': g.user_id,
            'name': player.name if player else 'Аноним',
            'guess_lat': g.guess_lat, 'guess_lon': g.guess_lon,
            'distance': g.distance, 'score': g.score, 'time_taken': g.time_taken
        })

    scores = {duel.player1_id: duel.get_player_score(duel.player1_id),
              duel.player2_id: duel.get_player_score(duel.player2_id)}

    result_data = {
        'duel_id': duel_id, 'round_number': duel.current_round,
        'correct_lat': location.lat, 'correct_lon': location.lon, 'city': location.city,
        'players': players_data, 'total_scores': scores,
        'is_last_round': duel.current_round >= 5
    }
    send_to_duel_players(duel_id, 'round_result', result_data)
    next_round_ready[duel_id] = set()


def next_round(duel_id):
    duel = db.session.get(Duel, duel_id)
    if not duel:
        return

    if duel.current_round >= 5:
        finish_duel(duel_id)
    else:
        duel.current_round += 1
        duel.location_id = None
        duel.round_start_time = None
        db.session.commit()
        start_duel_round(duel_id)


def finish_duel(duel_id):
    cancel_round_timer(duel_id)

    duel = db.session.get(Duel, duel_id)
    if not duel:
        return

    duel.status = 'finished'
    duel.finished_at = datetime.datetime.utcnow()
    db.session.commit()

    score1 = duel.get_player_score(duel.player1_id)
    score2 = duel.get_player_score(duel.player2_id)
    winner_id = duel.player1_id if score1 > score2 else (duel.player2_id if score2 > score1 else None)

    finish_data = {
        'duel_id': duel_id,
        'total_scores': {duel.player1_id: score1, duel.player2_id: score2},
        'winner_id': winner_id, 'lobby_id': duel.lobby_id
    }
    send_to_duel_players(duel_id, 'duel_finished', finish_data)

    if duel.lobby_id and duel.lobby_id in active_lobbies:
        lobby = active_lobbies[duel.lobby_id]
        for p in lobby['players']:
            p['ready'] = False
        lobby['duel'] = None
        socketio.emit('lobby_update', {
            'lobby_id': duel.lobby_id, 'players': lobby['players'],
            'host': lobby['host'], 'can_rematch': True
        }, room=duel.lobby_id)

    duel_rooms.pop(duel_id, None)
    round_timers.pop(duel_id, None)
    next_round_ready.pop(duel_id, None)