from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
YANDEX_API_KEY = '8013b162-6b42-4997-9691-77b7074026e0'


def get_db():
    conn = sqlite3.connect('locations.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_random_location():
    conn = get_db()
    location = conn.execute("""
        SELECT id, lat, lon, city, country, description 
        FROM locations 
        ORDER BY RANDOM() 
        LIMIT 1
    """).fetchone()
    conn.close()

    if location:
        return dict(location)
    else:
        return {
            'id': 0,
            'lat': 55.753544,
            'lon': 37.621202,
            'city': 'Москва',
            'country': 'Россия',
            'description': 'Красная площадь'
        }


@app.route('/')
def index():
    session.clear()
    session['total_score'] = 0
    session['round_number'] = 1
    session['rounds_results'] = []
    return render_template('index.html')


@app.route('/game')
def game():
    if 'total_score' not in session:
        return redirect(url_for('index'))

    # Проверяем, не закончена ли игра
    if session['round_number'] > 5:
        return redirect(url_for('game_over'))

    location = get_random_location()
    session['current_location'] = location

    location_hint = f"{location['city']}, {location['country']}" if location.get('city') else None

    return render_template('game.html',
                           yandex_api_key=YANDEX_API_KEY,
                           lat=location['lat'],
                           lon=location['lon'],
                           location_id=location['id'],
                           location_hint=location_hint,
                           round_number=session['round_number'],
                           total_score=session['total_score'])


@app.route('/submit_guess', methods=['POST'])
def submit_guess():
    data = request.json

    location_id = data['location_id']
    guess_lat = data['guess_lat']
    guess_lon = data['guess_lon']
    distance = data['distance']
    score = data['score']

    # Сохраняем в БД
    conn = get_db()
    conn.execute("""
        INSERT INTO games (location_id, user_guess_lat, user_guess_lon, distance, score)
        VALUES (?, ?, ?, ?, ?)
    """, (location_id, guess_lat, guess_lon, distance, score))
    conn.commit()
    conn.close()

    # Обновляем счёт и раунд
    session['total_score'] = session.get('total_score', 0) + score
    session['round_number'] = session.get('round_number', 1) + 1

    # Сохраняем результат раунда
    rounds_results = session.get('rounds_results', [])
    rounds_results.append({
        'round': session['round_number'] - 1,
        'score': score,
        'distance': distance
    })
    session['rounds_results'] = rounds_results

    return jsonify({
        'status': 'ok',
        'total_score': session['total_score'],
        'round_score': score,
        'next_round': session['round_number']
    })


@app.route('/game_over')
def game_over():
    if 'total_score' not in session:
        return redirect(url_for('index'))

    total_score = session['total_score']
    rounds_results = session.get('rounds_results', [])
    rounds_played = len(rounds_results)

    avg_score = total_score / rounds_played if rounds_played > 0 else 0
    best_round = max([r['score'] for r in rounds_results]) if rounds_results else 0

    return render_template('game_over.html',
                           total_score=total_score,
                           rounds_played=rounds_played,
                           avg_score=round(avg_score),
                           best_round=best_round)


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
    app.run(debug=True)