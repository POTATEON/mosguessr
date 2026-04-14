from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
YANDEX_API_KEY = 'a4de04aa-6650-4616-990e-5c9e25c6ec9e'

# Города России с координатами центров (где точно есть панорамы)
RUSSIAN_CITIES = [
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

# Границы Москвы (для случайной генерации)
MOSCOW_BOUNDS = {
    'min_lat': 55.55,
    'max_lat': 55.95,
    'min_lon': 37.35,
    'max_lon': 37.90
}

# Вероятность выпадения другого города (10%)
SURPRISE_CITY_PROBABILITY = 0.1


def init_db():
    conn = get_db()

    # Создаём таблицы, если их нет
    conn.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL,
            lon REAL,
            city TEXT,
            country TEXT,
            description TEXT,
            UNIQUE(lat, lon)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER,
            user_guess_lat REAL,
            user_guess_lon REAL,
            distance REAL,
            score INTEGER,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Проверяем и добавляем недостающие колонки в games
    cursor = conn.execute("PRAGMA table_info(games)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'is_surprise' not in columns:
        print("Добавляю колонку is_surprise...")
        conn.execute("ALTER TABLE games ADD COLUMN is_surprise BOOLEAN DEFAULT 0")

    if 'actual_city' not in columns:
        print("Добавляю колонку actual_city...")
        conn.execute("ALTER TABLE games ADD COLUMN actual_city TEXT")

    conn.commit()
    conn.close()
    print("✅ База данных готова")

def generate_random_moscow_coords():
    """Генерирует случайные координаты в пределах Москвы"""
    lat = random.uniform(MOSCOW_BOUNDS['min_lat'], MOSCOW_BOUNDS['max_lat'])
    lon = random.uniform(MOSCOW_BOUNDS['min_lon'], MOSCOW_BOUNDS['max_lon'])
    return lat, lon, "Москва"


def get_random_city():
    """Случайно выбирает: либо Москва (90%), либо другой город (10%)"""
    if random.random() < SURPRISE_CITY_PROBABILITY:
        # Выбираем любой город кроме Москвы
        other_cities = [c for c in RUSSIAN_CITIES if c["name"] != "Москва"]
        city = random.choice(other_cities)
        return city["lat"], city["lon"], city["name"]
    else:
        return generate_random_moscow_coords()


def get_db():
    conn = sqlite3.connect('locations.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL,
            lon REAL,
            city TEXT,
            country TEXT,
            description TEXT,
            UNIQUE(lat, lon)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER,
            user_guess_lat REAL,
            user_guess_lon REAL,
            distance REAL,
            score INTEGER,
            is_surprise BOOLEAN DEFAULT 0,
            actual_city TEXT,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_panorama_location(lat, lon, city="Москва"):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO locations (lat, lon, city, country) VALUES (?, ?, ?, ?)",
            (lat, lon, city, 'Россия')
        )
        conn.commit()
        if cursor.lastrowid == 0:
            row = conn.execute("SELECT id FROM locations WHERE lat=? AND lon=?", (lat, lon)).fetchone()
            return row['id'] if row else 0
        return cursor.lastrowid
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        return 0
    finally:
        conn.close()


@app.route('/')
def index():
    session.clear()
    session['total_score'] = 0
    session['round_number'] = 1
    session['round_scores'] = []
    session['surprises_found'] = 0
    return render_template('index.html')


@app.route('/game')
def game():
    if 'total_score' not in session:
        session['total_score'] = 0
        session['round_number'] = 1
        session['round_scores'] = []
        session['surprises_found'] = 0

    if session['round_number'] > 5:
        return redirect(url_for('game_over'))

    # Получаем координаты и название города
    search_lat, search_lon, city_name = get_random_city()

    # Сохраняем в сессии информацию о том, сюрприз это или нет
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
    data = request.json
    lat = data['lat']
    lon = data['lon']

    city = session.get('current_city', 'Москва')
    location_id = save_panorama_location(lat, lon, city)
    session['current_location'] = {'id': location_id, 'lat': lat, 'lon': lon}

    return jsonify({'status': 'ok', 'location_id': location_id})


@app.route('/submit_guess', methods=['POST'])
def submit_guess():
    data = request.json

    location_id = data['location_id']
    guess_lat = data['guess_lat']
    guess_lon = data['guess_lon']
    distance = data['distance']
    score = data['score']

    is_surprise = session.get('is_surprise', False)
    actual_city = session.get('current_city', 'Москва')

    conn = get_db()
    conn.execute("""
        INSERT INTO games (location_id, user_guess_lat, user_guess_lon, distance, score, is_surprise, actual_city)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (location_id, guess_lat, guess_lon, distance, score, is_surprise, actual_city))
    conn.commit()
    conn.close()

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
        'is_surprise': is_surprise,
        'actual_city': actual_city
    })


@app.route('/game_over')
def game_over():
    total_score = session.get('total_score', 0)
    round_number = session.get('round_number', 6)
    rounds_played = min(round_number - 1, 5)
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
    session.clear()
    session['total_score'] = 0
    session['round_number'] = 1
    session['round_scores'] = []
    session['surprises_found'] = 0
    return redirect(url_for('game'))


@app.route('/leaderboard')
def leaderboard():
    conn = get_db()
    games = conn.execute("""
        SELECT g.*, l.description, l.city 
        FROM games g 
        JOIN locations l ON g.location_id = l.id 
        ORDER BY g.score DESC 
        LIMIT 20
    """).fetchall()
    conn.close()
    return render_template('leaderboard.html', games=games)


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port='5000', debug=True)