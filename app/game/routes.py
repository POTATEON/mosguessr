import traceback

from flask import render_template, request, jsonify, redirect, url_for
from flask import session, current_app
from flask import render_template, request, jsonify, redirect, url_for, flash
from app.utils.avatar import generate_avatar_svg
from app.utils.helpers import login_required, get_current_user
from app.models.user import User
from app.auth.forms import AvatarForm
from app.extensions import db
from app.game import bp
from app.models.game import Game
from app.models.location import Location
from app.models.user import User
from app.utils.geo import get_random_city, calculate_score, haversine
from app.utils.helpers import login_required, get_current_user


@bp.route('/game')
@login_required
def game():
    if 'total_score' not in session:
        session['total_score'] = 0
        session['round_number'] = 1
        session['round_scores'] = []
        session['surprises_found'] = 0

    if session['round_number'] > 5:
        return redirect(url_for('game.game_over'))

    search_lat, search_lon, city_name = get_random_city()
    session['current_city'] = city_name
    session['is_surprise'] = (city_name != "Москва")

    return render_template('game.html',
                           yandex_api_key=current_app.config['YANDEX_API_KEY'],
                           search_lat=search_lat,
                           search_lon=search_lon,
                           round_number=session['round_number'],
                           total_score=session['total_score'])

@bp.route('/save_panorama', methods=['POST'])
def save_panorama():
    data = request.json
    lat = data['lat']
    lon = data['lon']
    city = session.get('current_city', 'Москва')

    location = db.session.query(Location).filter(
        Location.lat == lat, Location.lon == lon
    ).first()

    if not location:
        location = Location(lat=lat, lon=lon, city=city)
        db.session.add(location)
        db.session.commit()

    session['current_location'] = {
        'id': location.id,
        'lat': lat,
        'lon': lon,
        'city': city
    }

    return jsonify({'status': 'ok', 'location_id': location.id})

@bp.route('/submit_guess', methods=['POST'])
def submit_guess():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400

        location_data = session.get('current_location', {})
        location_id = location_data.get('id')
        if not location_id:
            return jsonify({'error': 'Локация не найдена в сессии'}), 400

        guess_lat = data.get('guess_lat')
        guess_lon = data.get('guess_lon')
        if guess_lat is None or guess_lon is None:
            return jsonify({'error': 'Не переданы координаты'}), 400

        real_location = db.session.get(Location, location_id)
        if not real_location:
            return jsonify({'error': 'Локация не найдена в БД'}), 400

        real_lat = real_location.lat
        real_lon = real_location.lon
        actual_city = real_location.city

        distance = haversine(guess_lat, guess_lon, real_lat, real_lon)
        distance_km = distance / 1000.0
        is_surprise = (actual_city != "Москва")
        score = calculate_score(distance_km, is_surprise)

        user_id = session.get('user_id')
        game = Game(
            user_id=user_id,
            location_id=location_id,
            user_guess_lat=guess_lat,
            user_guess_lon=guess_lon,
            distance=distance,
            score=score,
            is_surprise=is_surprise,
            actual_city=actual_city
        )
        db.session.add(game)
        db.session.commit()

        session['total_score'] = session.get('total_score', 0) + score
        session['round_number'] = session.get('round_number', 1) + 1

        if is_surprise:
            session['surprises_found'] = session.get('surprises_found', 0) + 1

        scores = session.get('round_scores', [])
        scores.append(score)
        session['round_scores'] = scores

        return jsonify({
            'status': 'ok',
            'total_score': session['total_score'],
            'round_score': score,
            'distance_km': round(distance_km, 2),
            'is_surprise': is_surprise,
            'actual_city': actual_city,
            'real_lat': real_lat,
            'real_lon': real_lon
        })

    except Exception as e:
        print("=" * 50)
        print("ОШИБКА в submit_guess:")
        traceback.print_exc()
        print("=" * 50)
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500

@bp.route('/game_over')
def game_over():
    total_score = session.get('total_score', 0)
    rounds_played = min(session.get('round_number', 6) - 1, 5)
    round_scores = session.get('round_scores', [])
    surprises_found = session.get('surprises_found', 0)

    avg_score = round(total_score / rounds_played) if rounds_played > 0 else 0
    best_round = max(round_scores) if round_scores else 0

    return render_template('game_over.html',
                           total_score=total_score,
                           rounds_played=rounds_played,
                           avg_score=avg_score,
                           best_round=best_round,
                           surprises_found=surprises_found)

@bp.route('/reset_game')
def reset_game():
    session.pop('total_score', None)
    session.pop('round_number', None)
    session.pop('round_scores', None)
    session.pop('surprises_found', None)
    session.pop('current_city', None)
    session.pop('is_surprise', None)
    session.pop('current_location', None)
    return redirect(url_for('game.game'))


@bp.route('/leaderboard')
def leaderboard():
    """HTML-страница с таблицей рекордов."""
    from sqlalchemy import func

    # Группируем по пользователю, суммируем очки
    results = (
        db.session.query(
            User.name,
            func.sum(Game.score).label('total_score'),
            func.max(Game.score).label('best_score'),
            func.count(Game.id).label('games_played'),
            func.max(Game.played_at).label('last_played')
        )
        .join(User, Game.user_id == User.id, isouter=True)
        .group_by(User.id, User.name)
        .order_by(func.sum(Game.score).desc())
        .limit(20)
        .all()
    )

    # Преобразуем в удобный формат для шаблона
    leaderboard = []
    for row in results:
        leaderboard.append({
            'name': row.name or 'Аноним',
            'total_score': int(row.total_score),
            'best_score': int(row.best_score),
            'games_played': row.games_played,
            'last_played': row.last_played
        })

    return render_template('leaderboard.html', leaderboard=leaderboard)

@bp.route('/duel')
@login_required
def duel_page():
    """Страница выбора режима дуэли (очередь или лобби)"""
    return render_template('duel_menu.html')

@bp.route('/duel/queue')
@login_required
def duel_queue():
    """Страница ожидания в очереди"""
    user = get_current_user()
    return render_template('duel_queue.html', user=user)

@bp.route('/duel/lobby/<lobby_id>')
@login_required
def duel_lobby(lobby_id):
    """Страница лобби"""
    user = get_current_user()
    return render_template('duel_lobby.html', lobby_id=lobby_id, user=user)

@bp.route('/duel/match')
@login_required
def duel_match():
    """Страница самой дуэли"""
    user = get_current_user()
    return render_template('duel_match.html',
                           yandex_api_key=current_app.config['YANDEX_API_KEY'],
                           user=user)

@bp.route('/duel/create')
@login_required
def duel_create():
    """Страница дуэли с созданием панорам"""
    user = get_current_user()
    return render_template('duel_create.html',
                           yandex_api_key=current_app.config['YANDEX_API_KEY'],
                           user=user)

@bp.route('/duel/create/queue')
@login_required
def duel_create_queue():
    """Страница очереди для режима создания панорам"""
    user = get_current_user()
    return render_template('duel_create_queue.html', user=user)

@bp.route('/duel/create/match')
@login_required
def duel_create_match():
    """Страница самой игры в режиме создания панорам"""
    user = get_current_user()
    return render_template('duel_create.html',
                           yandex_api_key=current_app.config['YANDEX_API_KEY'],
                           user=user)


@bp.route('/profile')
@login_required
def profile():
    """Страница профиля пользователя"""
    user = get_current_user()
    form = AvatarForm()
    return render_template('profile.html', user=user, form=form)


@bp.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    """Загрузить новый аватар"""
    user = get_current_user()

    if 'avatar' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('game.profile'))

    file = request.files['avatar']
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('game.profile'))

    # Исправлено: убираем .filestream, используем file напрямую
    if user.set_avatar(file):
        db.session.commit()
        flash('Аватар успешно обновлен!', 'success')
    else:
        flash('Ошибка при загрузке аватара', 'error')

    return redirect(url_for('game.profile'))

@bp.route('/remove_avatar', methods=['POST'])
@login_required
def remove_avatar():
    """Удалить загруженный аватар и вернуть SVG"""
    user = get_current_user()
    user.set_avatar_to_svg()
    db.session.commit()
    flash('Фото удалено, используется аватар по умолчанию', 'success')
    return redirect(url_for('game.profile'))


@bp.route('/avatar/<int:user_id>')
def user_avatar(user_id):
    """Получить аватар пользователя (рендерит SVG или редиректит на фото)"""
    user = db.session.get(User, user_id)
    if not user:
        return "User not found", 404

    if user.avatar_type == 'upload' and user.avatar_url:
        return redirect(user.avatar_url)
    else:
        svg = user.get_avatar_svg(200)
        return Response(svg, mimetype='image/svg+xml')