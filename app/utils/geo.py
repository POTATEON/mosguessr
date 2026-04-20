import random
import math

MOSCOW_BOUNDS = {
    'min_lat': 55.55, 'max_lat': 55.95,
    'min_lon': 37.35, 'max_lon': 37.90
}
SURPRISE_CITY_PROBABILITY = 0.1

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

def haversine(lat1, lon1, lat2, lon2):
    """Расстояние в метрах между двумя координатами."""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_score(distance_km, is_surprise_city):
    """Подсчёт очков."""
    if is_surprise_city and distance_km <= 20:
        return 52000
    if distance_km >= 10:
        return 0
    if distance_km <= 0.1:
        return 5000
    return round(5000 * (1 - (distance_km - 0.1) / 9.9))

def generate_random_moscow_coords():
    lat = random.uniform(MOSCOW_BOUNDS['min_lat'], MOSCOW_BOUNDS['max_lat'])
    lon = random.uniform(MOSCOW_BOUNDS['min_lon'], MOSCOW_BOUNDS['max_lon'])
    return lat, lon, "Москва"

def get_random_city():
    if random.random() < SURPRISE_CITY_PROBABILITY:
        other_cities = [c for c in RUSSIAN_CITIES if c["name"] != "Москва"]
        city = random.choice(other_cities)
        return city["lat"], city["lon"], city["name"]
    return generate_random_moscow_coords()