import os
import random
import math
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

# Импорты из папки data
from data import db_session
from data.models import User, Location, Game

# ========== НАСТРОЙКА ПРИЛОЖЕНИЯ ==========
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
YANDEX_API_KEY = os.environ.get('YANDEX_API_KEY') or 'a4de04aa-6650-4616-990e-5c9e25c6ec9e'


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def haversine(lat1, lon1, lat2, lon2):
    """Формула гаверсинуса для расчета расстояния"""
    R = 6371000  # Радиус Земли в метрах
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calculate_score(distance_km, is_surprise_city):
    """Подсчет очков на сервере"""
    if is_surprise_city and distance_km <= 20:
        return 52000  # Джекпот
    if distance_km >= 10:
        return 0
    if distance_km <= 0.1:
        return 5000
    return round(5000 * (1 - (distance_km - 0.1) / 9.9))


# ========== КОНСТАНТЫ ==========
RUSSIAN_CITIES = [
    {"name": "Москва", "lat": 55.755826, "lon": 37.617300},
    {"name": "Санкт-Петербург", "lat": 59.934280, "lon": 30.335099},
    {"name": "Казань", "lat": 55.796127, "lon": 49.106405},
    {"name": "Екатеринбург", "lat": 56.838926, "lon": 60.605703},
    {"name": "Нижний Новгород", "lat": 56.326797, "lon": 44.006516},
    {"name": "Новосибирск", "lat": 55.030204, "lon": 82.920430},
    {"name": "Владивосток", "lat": 43.115542, "lon": 131.885494},
    {"name": "Сочи", "lat": 43.585472, "lon": 39.723098},
    {"name": "Калининград", "lat": 54.710426, "lon": 20.452214},
    {"name": "Краснодар", "lat": 45.035470, "lon": 38.975313},
]

MOSCOW_BOUNDS = {
    'min_lat': 55.55, 'max_lat': 55.95,
    'min_lon': 37.35, 'max_lon': 37.90
}
SURPRISE_CITY_PROBABILITY = 0.1


def generate_random_moscow_coords():
    """Генерация случайных координат в Москве"""
    lat = random.uniform(MOSCOW_BOUNDS['min_lat'], MOSCOW_BOUNDS['max_lat'])
    lon = random.uniform(MOSCOW_BOUNDS['min_lon'], MOSCOW_BOUNDS['max_lon'])
    return lat, lon, "Москва"


def get_random_city():
    """Выбор города: Москва (90%) или другой (10%)"""
    if random.random() < SURPRISE_CITY_PROBABILITY:
        other_cities = [c for c in RUSSIAN_CITIES if c["name"] != "Москва"]
        city = random.choice(other_cities)
        return city["lat"], city["lon"], city["name"]
    return generate_random_moscow_coords()


def get_current_user():
    """Получение текущего пользователя из сессии"""
    if 'user_id' in session:
        db_sess = db_session.create_session()
        user = db_sess.get(User, session['user_id'])
        db_sess.close()
        return user
    return None


# ========== МАРШРУТЫ ==========
@app.route('/')
def index():
    """Главная страница"""
    user = get_current_user()
    return render_template('index.html', user=user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация пользователя (как в уроке WEB 3)"""
    if request.method == 'GET':
        return render_template('register.html')

    email = request.form.get('email')
    password = request.form.get('password')
    password_again = request.form.get('password_again')
    name = request.form.get('name')

    if password != password_again:
        return render_template('register.html', message="Пароли не совпадают")

    db_sess = db_session.create_session()
    if db_sess.query(User).filter(User.email == email).first():
        return render_template('register.html', message="Такой пользователь уже есть")

    user = User(name=name, email=email)
    user.set_password(password)
    db_sess.add(user)
    db_sess.commit()

    session['user_id'] = user.id
    session['user_name'] = user.name

    return redirect('/')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Авторизация (как в уроке WEB 4)"""
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form.get('email')
    password = request.form.get('password')

    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.email == email).first()

    if user and user.check_password(password):
        session['user_id'] = user.id
        session['user_name'] = user.name
        return redirect('/')

    return render_template('login.html', message="Неправильный логин или пароль")


@app.route('/logout')
def logout():
    """Выход из системы"""
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect('/')


@app.route('/game')
def game():
    """Игровой раунд"""
    if 'total_score' not in session:
        session['total_score'] = 0
        session['round_number'] = 1
        session['round_scores'] = []
        session['surprises_found'] = 0

    if session['round_number'] > 5:
        return redirect(url_for('game_over'))

    search_lat, search_lon, city_name = get_random_city()
    session['current_city'] = city_name
    session['is_surprise'] = (city_name != "Москва")

    return render_template('game.html',
                           yandex_api_key=YANDEX_API_KEY,
                           search_lat=search_lat,
                           search_lon=search_lon,
                           round_number=session['round_number'],
                           total_score=session['total_score'])


@app.route('/save_panorama', methods=['POST'])
def save_panorama():
    """Сохранение панорамы в БД"""
    data = request.json
    lat = data['lat']
    lon = data['lon']
    city = session.get('current_city', 'Москва')

    db_sess = db_session.create_session()

    # Проверяем, существует ли уже такая локация
    location = db_sess.query(Location).filter(
        Location.lat == lat, Location.lon == lon
    ).first()

    if not location:
        location = Location(lat=lat, lon=lon, city=city)
        db_sess.add(location)
        db_sess.commit()

    session['current_location'] = {
        'id': location.id,
        'lat': lat,
        'lon': lon,
        'city': city
    }

    return jsonify({'status': 'ok', 'location_id': location.id})


import traceback
import sys


# ... (весь код до submit_guess остается без изменений)

@app.route('/submit_guess', methods=['POST'])
def submit_guess():
    """Обработка догадки игрока"""
    try:
        data = request.json

        # Проверяем, что данные пришли
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400

        # Получаем данные из сессии
        location_data = session.get('current_location', {})
        location_id = location_data.get('id')

        if not location_id:
            return jsonify({'error': 'Локация не найдена в сессии'}), 400

        guess_lat = data.get('guess_lat')
        guess_lon = data.get('guess_lon')

        if guess_lat is None or guess_lon is None:
            return jsonify({'error': 'Не переданы координаты'}), 400

        # Загружаем правильные координаты из БД
        db_sess = db_session.create_session()
        real_location = db_sess.get(Location, location_id)

        if not real_location:
            db_sess.close()
            return jsonify({'error': 'Локация не найдена в БД'}), 400

        real_lat = real_location.lat
        real_lon = real_location.lon
        actual_city = real_location.city

        # Расчет расстояния и очков
        distance = haversine(guess_lat, guess_lon, real_lat, real_lon)
        distance_km = distance / 1000.0
        is_surprise = (actual_city != "Москва")
        score = calculate_score(distance_km, is_surprise)

        # Сохраняем результат игры
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
        db_sess.add(game)
        db_sess.commit()
        db_sess.close()

        # Обновляем сессию
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
        # Выводим полную ошибку в консоль
        print("=" * 50)
        print("ОШИБКА в submit_guess:")
        traceback.print_exc()
        print("=" * 50)

        # Возвращаем JSON с ошибкой
        return jsonify({
            'error': str(e),
            'type': type(e).__name__
        }), 500

@app.route('/game_over')
def game_over():
    """Страница с результатами"""
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


@app.route('/reset_game')
def reset_game():
    """Сброс игры"""
    session.pop('total_score', None)
    session.pop('round_number', None)
    session.pop('round_scores', None)
    session.pop('surprises_found', None)
    session.pop('current_city', None)
    session.pop('is_surprise', None)
    session.pop('current_location', None)
    return redirect(url_for('game'))


@app.route('/leaderboard')
def leaderboard():
    """Таблица рекордов"""
    db_sess = db_session.create_session()
    games = db_sess.query(Game).order_by(Game.score.desc()).limit(20).all()
    return render_template('leaderboard.html', games=games)


# ========== ЗАПУСК ПРИЛОЖЕНИЯ ==========
if __name__ == '__main__':
    db_session.global_init("../db/locations.db")
    app.run(host='0.0.0.0', port=5000, debug=True)