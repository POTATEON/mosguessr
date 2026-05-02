"""События классической дуэли"""
import time
import datetime
from app.models.location import Location
from app.models.user import User
from flask import session, request
from flask_socketio import emit
from app.extensions import socketio, db
from app.models.duel import Duel
from app.utils.geo import get_random_city
from .state import (
    duel_rooms, next_round_ready,
    panorama_regeneration_count, panorama_regeneration_lock
)
from .helpers import save_location, send_to_duel_players, send_to_player
from .duel_manager import start_duel_round, submit_guess, next_round


@socketio.on('submit_duel_guess')
def handle_duel_guess(data=None):
    duel_id = data.get('duel_id')
    user_id = session.get('user_id')
    success, error = submit_guess(duel_id, user_id, data.get('guess_lat'), data.get('guess_lon'))
    if not success:
        emit('error', {'message': error})


@socketio.on('next_round')
def handle_next_round(data=None):
    duel_id = data.get('duel_id')
    user_id = session.get('user_id')
    if duel_id not in next_round_ready:
        next_round_ready[duel_id] = set()
    next_round_ready[duel_id].add(user_id)
    send_to_duel_players(duel_id, 'player_ready_next', {'user_id': user_id})

    if len(next_round_ready.get(duel_id, set())) >= 2:
        next_round_ready.pop(duel_id, None)
        with panorama_regeneration_lock:
            panorama_regeneration_count.pop(duel_id, None)
            panorama_regeneration_count.pop(f"{duel_id}_time", None)
        next_round(duel_id)


@socketio.on('join_duel_from_queue')
def handle_join_duel_from_queue(data=None):
    """
    Переподключение игрока к дуэли после редиректа.
    
    ★ ИСПРАВЛЕНИЕ: Теперь отправляем duel_found с opponent_id и opponent_name
    при переподключении, чтобы инлайн-скрипт VS-экрана мог загрузить аватарку.
    """
    duel_id = data.get('duel_id')
    user_id = session.get('user_id')

    if duel_id not in duel_rooms:
        duel_rooms[duel_id] = {}
    duel_rooms[duel_id][user_id] = request.sid

    duel = db.session.get(Duel, duel_id)
    if not duel or duel.status != 'in_progress':
        return

    # ★ НОВОЕ: Отправляем данные о сопернике при переподключении
    opponent_id = duel.player2_id if user_id == duel.player1_id else duel.player1_id
    opponent = db.session.get(User, opponent_id)
    opponent_name = opponent.name if opponent else 'Соперник'
    
    send_to_player(duel_id, user_id, 'duel_found', {
        'duel_id': duel_id,
        'opponent_name': opponent_name,
        'opponent_id': opponent_id,
        'my_user_id': user_id
    })

    # Если оба подключены
    if len(duel_rooms[duel_id]) == 2:
        # Если раунд уже запущен (есть location_id) — отправляем текущие координаты новому игроку
        if duel.location_id:
            location = db.session.get(Location, duel.location_id)
            if location:
                send_to_player(duel_id, user_id, 'start_round', {
                    'duel_id': duel_id,
                    'round_number': duel.current_round,
                    'search_lat': location.lat,
                    'search_lon': location.lon,
                    'city': location.city
                })
        else:
            # Раунд ещё не запущен — запускаем
            start_duel_round(duel_id)


@socketio.on('panorama_not_found')
def handle_panorama_not_found(data=None):
    """
    Обработчик запроса на регенерацию панорамы.
    
    ВАЖНО: Этот метод отправляет новый start_round ОБОИМ игрокам.
    Клиент использует токен отмены (currentLoadToken) чтобы отбросить
    результаты устаревших вызовов loadPanorama, которые могли 
    выполняться в момент получения нового start_round.
    """
    duel_id = data.get('duel_id')
    user_id = session.get('user_id')

    duel = db.session.get(Duel, duel_id)
    if not duel or duel.status != 'in_progress':
        return

    # 🔥 Проверяем: если хоть кто-то уже ответил в этом раунде — не регенерируем
    existing_guesses = duel.guesses.filter_by(round_number=duel.current_round).count()
    if existing_guesses > 0:
        print(f"[PANORAMA] Round {duel.current_round} already has guesses, not regenerating")
        return

    # Генерируем новые координаты
    search_lat, search_lon, city_name = get_random_city()
    location = save_location(search_lat, search_lon, city_name)

    duel.location_id = location.id
    duel.round_start_time = datetime.datetime.utcnow()
    db.session.commit()

    # Отправляем ОБОИМ игрокам
    send_to_duel_players(duel_id, 'start_round', {
        'duel_id': duel_id,
        'round_number': duel.current_round,
        'search_lat': search_lat,
        'search_lon': search_lon,
        'city': city_name
    })