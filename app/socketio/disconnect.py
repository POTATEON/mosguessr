"""Обработка отключения"""
from flask import session, current_app
from app.extensions import socketio, db
from app.models.duel import Duel
from .state import waiting_players, active_lobbies, duel_rooms, round_timers, next_round_ready, waiting_lock
from .helpers import get_duel_player_sids, cancel_round_timer


@socketio.on('disconnect')
def handle_disconnect(reason=None):
    user_id = session.get('user_id')
    if not user_id:
        return

    global waiting_players
    with waiting_lock:
        waiting_players = [p for p in waiting_players if p['user_id'] != user_id]

    for duel_id, room in list(duel_rooms.items()):
        if user_id in room:
            app = current_app._get_current_object()
            socketio.start_background_task(_delayed_disconnect_check, app, duel_id, user_id)
            break

    for lobby_id, lobby in list(active_lobbies.items()):
        lobby['players'] = [p for p in lobby['players'] if p['user_id'] != user_id]
        if not lobby['players']:
            active_lobbies.pop(lobby_id, None)
        else:
            socketio.emit('lobby_update', {
                'lobby_id': lobby_id, 'players': lobby['players'], 'host': lobby['host']
            }, room=lobby_id)


def _delayed_disconnect_check(app, duel_id, user_id):
    socketio.sleep(5)

    if duel_id in duel_rooms and user_id in duel_rooms[duel_id]:
        return

    cancel_round_timer(duel_id)

    with app.app_context():
        duel = db.session.get(Duel, duel_id)
        if duel and duel.status == 'in_progress':
            for sid in get_duel_player_sids(duel_id):
                socketio.emit('opponent_disconnected', {'user_id': user_id}, room=sid)

            duel.status = 'finished'
            duel.finished_at = db.func.now()
            db.session.commit()

    duel_rooms.pop(duel_id, None)
    round_timers.pop(duel_id, None)
    next_round_ready.pop(duel_id, None)