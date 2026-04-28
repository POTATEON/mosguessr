"""Вспомогательные функции"""
from app.extensions import socketio, db
from app.models.location import Location
from .state import duel_rooms, round_timers


def save_location(lat, lon, city):
    """Сохранить локацию в БД и вернуть её"""
    location = db.session.query(Location).filter(
        Location.lat == lat, Location.lon == lon
    ).first()
    if not location:
        location = Location(lat=lat, lon=lon, city=city)
        db.session.add(location)
        db.session.commit()
    return location


def calculate_speed_bonus(time_taken):
    """Бонус за скорость ответа"""
    if time_taken is None:
        return 0
    if time_taken < 10:
        return 1000
    elif time_taken < 20:
        return 500
    elif time_taken < 30:
        return 250
    elif time_taken < 45:
        return 100
    return 0


def get_duel_player_sids(duel_id):
    """Получить sid'ы обоих игроков дуэли"""
    return list(duel_rooms.get(duel_id, {}).values())


def send_to_duel_players(duel_id, event, data=None):
    """Отправить событие обоим игрокам дуэли"""
    for sid in get_duel_player_sids(duel_id):
        try:
            socketio.emit(event, data, room=sid)
        except Exception as e:
            print(f"[ERROR] Failed to send {event} to {sid}: {e}")


def send_to_player(duel_id, user_id, event, data):
    """Отправить событие конкретному игроку"""
    room = duel_rooms.get(duel_id, {})
    sid = room.get(user_id)
    if sid:
        try:
            socketio.emit(event, data, room=sid)
        except Exception as e:
            print(f"[ERROR] Failed to send to player {user_id}: {e}")


def send_to_duel_except(duel_id, exclude_user_id, event, data):
    """Отправить событие всем кроме указанного игрока"""
    room = duel_rooms.get(duel_id, {})
    for user_id, sid in room.items():
        if user_id != exclude_user_id:
            try:
                socketio.emit(event, data, room=sid)
            except Exception as e:
                print(f"[ERROR] Failed to send to player {user_id}: {e}")


def cancel_round_timer(duel_id):
    """Отменить таймер раунда"""
    if duel_id in round_timers:
        del round_timers[duel_id]