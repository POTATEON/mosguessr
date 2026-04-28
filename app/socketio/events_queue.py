"""События очереди и лобби"""
import uuid
from flask import session, request
from flask_socketio import emit, join_room
from app.extensions import socketio
from .state import (
    waiting_players, active_lobbies, waiting_lock,
    creator_waiting_players, creator_waiting_lock
)
from .duel_manager import create_duel
from .creator_manager import create_creator_duel


@socketio.on('join_duel_queue')
def handle_join_queue(data=None):
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'Аноним')
    if not user_id:
        emit('error', {'message': 'Необходима авторизация'})
        return

    with waiting_lock:
        global waiting_players
        waiting_players = [p for p in waiting_players if p['user_id'] != user_id]
        waiting_players.append({'user_id': user_id, 'name': user_name, 'sid': request.sid})
        position = len(waiting_players)

        if len(waiting_players) >= 2:
            p1 = waiting_players.pop(0)
            p2 = waiting_players.pop(0)
            create_duel(p1, p2)

    emit('queue_status', {'position': position, 'in_queue': True})


@socketio.on('leave_duel_queue')
def handle_leave_queue():
    global waiting_players
    user_id = session.get('user_id')
    with waiting_lock:
        waiting_players = [p for p in waiting_players if p['user_id'] != user_id]
    emit('queue_status', {'position': 0, 'in_queue': False})


@socketio.on('create_lobby')
def handle_create_lobby():
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'Аноним')
    if not user_id:
        emit('error', {'message': 'Необходима авторизация'})
        return

    lobby_id = str(uuid.uuid4())[:8]
    active_lobbies[lobby_id] = {
        'players': [{'user_id': user_id, 'name': user_name, 'sid': request.sid, 'ready': False}],
        'host': user_id,
        'duel': None
    }
    join_room(lobby_id)
    emit('lobby_created', {'lobby_id': lobby_id, 'players': active_lobbies[lobby_id]['players']})


@socketio.on('join_lobby')
def handle_join_lobby(data=None):
    lobby_id = data.get('lobby_id')
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'Аноним')
    if not user_id:
        emit('error', {'message': 'Необходима авторизация'})
        return

    if lobby_id not in active_lobbies:
        active_lobbies[lobby_id] = {'players': [], 'host': user_id, 'duel': None}

    lobby = active_lobbies[lobby_id]
    existing = [p for p in lobby['players'] if p['user_id'] == user_id]
    if existing:
        existing[0]['sid'] = request.sid
    else:
        if len(lobby['players']) >= 2:
            emit('error', {'message': 'Лобби заполнено'})
            return
        lobby['players'].append({'user_id': user_id, 'name': user_name, 'sid': request.sid, 'ready': False})

    join_room(lobby_id)
    emit('lobby_update', {'lobby_id': lobby_id, 'players': lobby['players'], 'host': lobby['host']}, room=lobby_id)


@socketio.on('player_ready')
def handle_player_ready(data=None):
    lobby_id = data.get('lobby_id')
    user_id = session.get('user_id')
    if lobby_id not in active_lobbies:
        return

    lobby = active_lobbies[lobby_id]
    for p in lobby['players']:
        if p['user_id'] == user_id:
            p['ready'] = True
            break

    emit('lobby_update', {'lobby_id': lobby_id, 'players': lobby['players'], 'host': lobby['host']}, room=lobby_id)

    if len(lobby['players']) == 2 and all(p['ready'] for p in lobby['players']):
        p1, p2 = lobby['players']
        create_duel(p1, p2, lobby_id)


@socketio.on('join_creator_queue')
def handle_join_creator_queue(data=None):
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'Аноним')
    if not user_id:
        emit('error', {'message': 'Необходима авторизация'})
        return

    with creator_waiting_lock:
        global creator_waiting_players
        creator_waiting_players = [p for p in creator_waiting_players if p['user_id'] != user_id]
        creator_waiting_players.append({'user_id': user_id, 'name': user_name, 'sid': request.sid})
        position = len(creator_waiting_players)

        if len(creator_waiting_players) >= 2:
            p1 = creator_waiting_players.pop(0)
            p2 = creator_waiting_players.pop(0)
            create_creator_duel(p1, p2)

    emit('queue_status', {'position': position, 'in_queue': True})


@socketio.on('leave_creator_queue')
def handle_leave_creator_queue():
    global creator_waiting_players
    user_id = session.get('user_id')
    with creator_waiting_lock:
        creator_waiting_players = [p for p in creator_waiting_players if p['user_id'] != user_id]
    emit('queue_status', {'position': 0, 'in_queue': False})