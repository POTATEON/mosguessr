"""Логика режима Создатель"""
import datetime
from flask import current_app
from app.extensions import socketio, db
from app.models.duel import Duel, DuelGuess
from app.models.location import Location
from app.models.user import User
from app.utils.geo import calculate_score, haversine
from .state import duel_rooms, creator_locations, creator_guesses, creator_timers
from .helpers import send_to_player, send_to_duel_except


def create_creator_duel(player1, player2, lobby_id=None):
    duel = Duel(
        player1_id=player1['user_id'], player2_id=player2['user_id'],
        status='in_progress', current_round=1, lobby_id=lobby_id
    )
    db.session.add(duel)
    db.session.commit()

    duel_rooms[duel.id] = {player1['user_id']: player1['sid'], player2['user_id']: player2['sid']}

    for player in [player1, player2]:
        opponent = player2 if player == player1 else player1
        socketio.emit('duel_found', {
            'duel_id': duel.id,
            'opponent_name': opponent['name'],
            'opponent_id': opponent['user_id'],
            'my_user_id': player['user_id'],
            'mode': 'creator',
            'lobby_id': lobby_id,
            'time_limit': 60  # Добавляем лимит времени
        }, room=player['sid'])

    # Запускаем таймер для фазы выбора (60 секунд)
    app = current_app._get_current_object()
    socketio.start_background_task(_creator_selection_timer, app, duel.id, 1)


def _creator_selection_timer(app, duel_id, round_num):
    """Таймер для фазы выбора локации (60 секунд)"""
    socketio.sleep(60)
    with app.app_context():
        duel = db.session.get(Duel, duel_id)
        if duel and duel.status == 'in_progress' and duel.current_round == round_num:
            # Проверяем, не началась ли уже фаза угадывания
            if len(creator_locations.get(duel_id, {})) < 2:
                locations = creator_locations.get(duel_id, {})

                # Для игроков, которые не выбрали локацию
                for user_id in [duel.player1_id, duel.player2_id]:
                    if user_id not in locations:
                        # Генерируем случайные координаты в Москве
                        import random
                        random_lat = 55.751244 + (random.random() - 0.5) * 0.1
                        random_lon = 37.618423 + (random.random() - 0.5) * 0.1

                        # Сохраняем случайную локацию
                        save_creator_location(duel_id, user_id, random_lat, random_lon)

                        send_to_player(duel_id, user_id, 'time_expired', {
                            'phase': 'selection',
                            'message': 'Время на выбор локации истекло. Выбрана случайная локация.'
                        })


def save_creator_location(duel_id, user_id, lat, lon):
    if duel_id not in creator_locations:
        creator_locations[duel_id] = {}
    creator_locations[duel_id][user_id] = {'lat': lat, 'lon': lon}

    location = Location(lat=lat, lon=lon, city='Москва')
    db.session.add(location)
    db.session.commit()

    send_to_duel_except(duel_id, user_id, 'opponent_selected_location', {'user_id': user_id})

    if len(creator_locations.get(duel_id, {})) >= 2:
        _start_guessing_phase(duel_id)


def _start_guessing_phase(duel_id):
    duel = db.session.get(Duel, duel_id)
    if not duel:
        return

    locations = creator_locations[duel_id]
    p1_id, p2_id = duel.player1_id, duel.player2_id

    send_to_player(duel_id, p1_id, 'start_guessing_phase', {
        'lat': locations[p2_id]['lat'], 'lon': locations[p2_id]['lon'],
        'round_number': duel.current_round,
        'time_limit': 120  # Отправляем лимит времени на клиент
    })
    send_to_player(duel_id, p2_id, 'start_guessing_phase', {
        'lat': locations[p1_id]['lat'], 'lon': locations[p1_id]['lon'],
        'round_number': duel.current_round,
        'time_limit': 120  # Отправляем лимит времени на клиент
    })

    creator_guesses[duel_id] = {}
    creator_timers[duel_id] = {'round': duel.current_round, 'started': datetime.datetime.utcnow()}

    app = current_app._get_current_object()
    # Запускаем таймер на 120 секунд (2 минуты) для фазы угадывания
    socketio.start_background_task(_creator_guessing_timer, app, duel_id, duel.current_round)


def _creator_guessing_timer(app, duel_id, round_num):
    """Таймер для фазы угадывания (120 секунд)"""
    socketio.sleep(120)
    with app.app_context():
        duel = db.session.get(Duel, duel_id)
        if duel and duel.status == 'in_progress' and duel.current_round == round_num:
            # Проверяем, есть ли уже результаты
            if len(creator_guesses.get(duel_id, {})) < 2:
                # Кто-то не успел сделать догадку
                current_guesses = creator_guesses.get(duel_id, {})

                # Для тех, кто не сделал догадку - ставим null координаты
                for user_id in [duel.player1_id, duel.player2_id]:
                    if user_id not in current_guesses:
                        creator_guesses[duel_id][user_id] = {'lat': None, 'lon': None}
                        send_to_player(duel_id, user_id, 'time_expired', {
                            'phase': 'guessing',
                            'message': 'Время на угадывание истекло'
                        })

                # Принудительно считаем результаты
                _calculate_creator_results(duel_id)


def save_creator_guess(duel_id, user_id, guess_lat, guess_lon):
    if duel_id not in creator_guesses:
        creator_guesses[duel_id] = {}
    creator_guesses[duel_id][user_id] = {'lat': guess_lat, 'lon': guess_lon}

    send_to_duel_except(duel_id, user_id, 'opponent_guessed', {'user_id': user_id})

    if len(creator_guesses.get(duel_id, {})) >= 2:
        _calculate_creator_results(duel_id)


def _calculate_creator_results(duel_id):
    creator_timers.pop(duel_id, None)

    duel = db.session.get(Duel, duel_id)
    if not duel:
        return

    locations = creator_locations.get(duel_id, {})
    guesses = creator_guesses.get(duel_id, {})

    if not locations or not guesses:
        return

    results = []
    for user_id in [duel.player1_id, duel.player2_id]:
        opponent_id = duel.player2_id if user_id == duel.player1_id else duel.player1_id
        opponent_location = locations.get(opponent_id)
        user_guess = guesses.get(user_id)

        distance = None
        distance_km = None
        score = 0

        if opponent_location and user_guess and user_guess.get('lat') is not None:
            distance = haversine(opponent_location['lat'], opponent_location['lon'],
                                 user_guess['lat'], user_guess['lon'])
            distance_km = distance / 1000.0
            score = calculate_score(distance_km, False)

        db.session.add(DuelGuess(
            duel_id=duel_id, user_id=user_id, round_number=duel.current_round,
            guess_lat=user_guess['lat'] if user_guess else None,
            guess_lon=user_guess['lon'] if user_guess else None,
            distance=distance, score=score
        ))

        user = db.session.get(User, user_id)
        results.append({'user_id': user_id, 'name': user.name if user else 'Аноним',
                        'distance': distance_km, 'score': score, 'guess': user_guess})

    db.session.commit()

    for user_id in [duel.player1_id, duel.player2_id]:
        opponent_id = duel.player2_id if user_id == duel.player1_id else duel.player1_id

        result_data = {
            'opponent_lat': locations[opponent_id]['lat'],
            'opponent_lon': locations[opponent_id]['lon'],
            'my_location': {'lat': locations[user_id]['lat'], 'lon': locations[user_id]['lon']},
            'my_guess': {'lat': guesses[user_id]['lat'], 'lon': guesses[user_id]['lon']} if user_id in guesses else None,
            'enemy_guess': {'lat': guesses[opponent_id]['lat'], 'lon': guesses[opponent_id]['lon']} if opponent_id in guesses else None,
            'players': [{'user_id': r['user_id'], 'name': r['name'], 'distance': r['distance'], 'score': r['score']} for r in results],
            'is_last_round': duel.current_round >= 3
        }
        send_to_player(duel_id, user_id, 'creator_round_result', result_data)

    creator_locations.pop(duel_id, None)
    creator_guesses.pop(duel_id, None)