"""События режима Создатель"""
from flask import session, request
from flask_socketio import emit
from app.extensions import socketio, db
from app.models.duel import Duel
from .state import duel_rooms, creator_locations
from .creator_manager import save_creator_location, save_creator_guess, _creator_selection_timer
from .duel_manager import finish_duel


@socketio.on('join_creator_duel')
def handle_join_creator_duel(data):
    duel_id = data.get('duel_id')
    user_id = session.get('user_id')
    if duel_id not in duel_rooms:
        duel_rooms[duel_id] = {}
    duel_rooms[duel_id][user_id] = request.sid
    emit('joined_creator_duel', {'duel_id': duel_id, 'user_id': user_id})


@socketio.on('creator_location_selected')
def handle_creator_location_selected(data):
    duel_id = data.get('duel_id')
    user_id = session.get('user_id')

    duel = db.session.get(Duel, duel_id)
    if not duel or duel.status != 'in_progress':
        emit('error', {'message': 'Дуэль неактивна'})
        return

    save_creator_location(duel_id, user_id, data.get('lat'), data.get('lon'))


@socketio.on('submit_creator_guess')
def handle_creator_guess(data):
    duel_id = data.get('duel_id')
    user_id = session.get('user_id')

    duel = db.session.get(Duel, duel_id)
    if not duel or duel.status != 'in_progress':
        emit('error', {'message': 'Дуэль неактивна'})
        return

    save_creator_guess(duel_id, user_id, data.get('guess_lat'), data.get('guess_lon'))


@socketio.on('next_creator_round')
def handle_next_creator_round(data):
    duel_id = data.get('duel_id')
    duel = db.session.get(Duel, duel_id)
    if not duel:
        return

    if duel.current_round >= 3:
        finish_duel(duel_id)
    else:
        duel.current_round += 1
        db.session.commit()

        # Запускаем новый таймер для фазы выбора
        app = current_app._get_current_object()
        socketio.start_background_task(_creator_selection_timer, app, duel_id, duel.current_round)