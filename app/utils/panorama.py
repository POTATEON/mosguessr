import requests
import random
import time
from flask import current_app


def find_panorama_in_moscow(max_attempts=20, radius_km=3):
    """
    Ищет панораму в Москве через API Яндекс.Панорам.
    Пробует разные точки в Москве пока не найдет панораму.

    Возвращает (lat, lon) или None если не найдено.
    """
    api_key = current_app.config['YANDEX_API_KEY']

    # Границы Москвы (примерные)
    MOSCOW_BOUNDS = {
        'lat_min': 55.55,
        'lat_max': 55.95,
        'lon_min': 37.35,
        'lon_max': 37.90
    }

    print(f"[PANORAMA] Searching for panorama in Moscow (max {max_attempts} attempts)")

    for attempt in range(max_attempts):
        # Генерируем случайную точку в Москве
        lat = random.uniform(MOSCOW_BOUNDS['lat_min'], MOSCOW_BOUNDS['lat_max'])
        lon = random.uniform(MOSCOW_BOUNDS['lon_min'], MOSCOW_BOUNDS['lon_max'])

        print(f"[PANORAMA] Attempt {attempt + 1}/{max_attempts}: {lat:.6f}, {lon:.6f}")

        # Проверяем через API Яндекс.Панорам
        url = f"https://api-maps.yandex.ru/services/panoramas/1.x/?l=stv&ll={lon},{lat}&origin=userAction&apikey={api_key}"

        try:
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()

                if 'data' in data and 'features' in data['data'] and len(data['data']['features']) > 0:
                    # Нашли панораму
                    feature = data['data']['features'][0]
                    coords = feature['geometry']['coordinates']
                    found_lon, found_lat = coords[0], coords[1]

                    # Проверяем, что панорама в Москве
                    if (MOSCOW_BOUNDS['lat_min'] <= found_lat <= MOSCOW_BOUNDS['lat_max'] and
                            MOSCOW_BOUNDS['lon_min'] <= found_lon <= MOSCOW_BOUNDS['lon_max']):

                        print(
                            f"[PANORAMA] Found panorama in Moscow at {found_lat:.6f}, {found_lon:.6f} (attempt {attempt + 1})")
                        return found_lat, found_lon
                    else:
                        print(f"[PANORAMA] Found panorama but outside Moscow bounds, skipping")
                else:
                    print(f"[PANORAMA] No panorama at this location")
            else:
                print(f"[PANORAMA] API returned status {response.status_code}")

        except requests.exceptions.Timeout:
            print(f"[PANORAMA] API timeout")
        except requests.exceptions.RequestException as e:
            print(f"[PANORAMA] API request error: {e}")
        except Exception as e:
            print(f"[PANORAMA] Unexpected error: {e}")

        # Небольшая задержка между попытками
        if attempt < max_attempts - 1:
            time.sleep(0.2)

    print(f"[PANORAMA] No panorama found in Moscow after {max_attempts} attempts")
    return None


def find_panorama_near_point(lat, lon, max_attempts=15, radius_km=2):
    """
    Ищет панораму рядом с заданной точкой.
    Пробует разные смещения от исходной точки.

    Возвращает (lat, lon) или None если не найдено.
    """
    api_key = current_app.config['YANDEX_API_KEY']

    print(f"[PANORAMA] Searching near {lat:.6f}, {lon:.6f} (radius {radius_km}km)")

    for attempt in range(max_attempts):
        if attempt == 0:
            # Первая попытка - точные координаты
            search_lat, search_lon = lat, lon
        else:
            # Случайное смещение в радиусе
            angle = random.uniform(0, 2 * 3.14159)
            distance = random.uniform(0.1, radius_km)

            # Переводим километры в градусы
            lat_offset = (distance / 111.32) * random.choice([-1, 1])
            lon_offset = (distance / (111.32 * abs(0.0001 + lat))) * random.choice([-1, 1])

            search_lat = lat + lat_offset
            search_lon = lon + lon_offset

        # Проверяем через API
        url = f"https://api-maps.yandex.ru/services/panoramas/1.x/?l=stv&ll={search_lon},{search_lat}&origin=userAction&apikey={api_key}"

        try:
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()

                if 'data' in data and 'features' in data['data'] and len(data['data']['features']) > 0:
                    feature = data['data']['features'][0]
                    coords = feature['geometry']['coordinates']
                    found_lon, found_lat = coords[0], coords[1]

                    print(f"[PANORAMA] Found panorama at {found_lat:.6f}, {found_lon:.6f} (attempt {attempt + 1})")
                    return found_lat, found_lon

        except Exception as e:
            print(f"[PANORAMA] Error: {e}")

        if attempt < max_attempts - 1:
            time.sleep(0.2)

    return None


def get_random_moscow_location_with_panorama():
    """
    Находит случайную точку в Москве с панорамой.
    Используется для дуэлей и одиночной игры.

    Возвращает (lat, lon, city_name)
    """
    from app.utils.geo import get_random_city

    print(f"[PANORAMA] Getting random Moscow location with panorama")

    # Сначала пробуем через get_random_city (может вернуть другой город для сюрпризов)
    search_lat, search_lon, city_name = get_random_city()

    print(f"[PANORAMA] Initial city: {city_name} at {search_lat:.4f}, {search_lon:.4f}")

    # Ищем панораму рядом с этой точкой
    result = find_panorama_near_point(search_lat, search_lon, max_attempts=15, radius_km=3)

    if result:
        lat, lon = result
        print(f"[PANORAMA] Found panorama for {city_name}: {lat:.6f}, {lon:.6f}")
        return lat, lon, city_name

    # Если не нашли рядом с городом - ищем по всей Москве
    print(f"[PANORAMA] No panorama near {city_name}, searching all Moscow")
    result = find_panorama_in_moscow(max_attempts=30)

    if result:
        lat, lon = result
        print(f"[PANORAMA] Found panorama in Moscow: {lat:.6f}, {lon:.6f}")
        return lat, lon, "Москва"

    # Запасной вариант - центр Москвы
    print(f"[PANORAMA] Using fallback: Red Square")
    fallback_lat, fallback_lon = 55.753544, 37.621202

    # Проверяем что там есть панорама
    result = find_panorama_near_point(fallback_lat, fallback_lon, max_attempts=5, radius_km=0.5)

    if result:
        lat, lon = result
        return lat, lon, "Москва (центр)"

    # Если даже центр не работает - возвращаем как есть
    return fallback_lat, fallback_lon, "Москва"


# Для обратной совместимости
def get_random_city_with_panorama(max_city_attempts=10, panorama_attempts_per_city=10):
    """
    Выбирает случайный город и находит в нём панораму.
    Для Москвы использует специальную логику поиска.
    """
    from app.utils.geo import get_random_city

    print(f"[PANORAMA] Starting search")

    # Пробуем несколько случайных городов
    for city_attempt in range(max_city_attempts):
        search_lat, search_lon, city_name = get_random_city()

        print(f"[PANORAMA] City attempt {city_attempt + 1}: {city_name}")

        if city_name == "Москва":
            # Для Москвы используем специальный поиск
            result = find_panorama_in_moscow(max_attempts=panorama_attempts_per_city)
        else:
            # Для других городов ищем рядом с точкой
            result = find_panorama_near_point(
                search_lat, search_lon,
                max_attempts=panorama_attempts_per_city,
                radius_km=5
            )

        if result:
            lat, lon = result
            print(f"[PANORAMA] Success: {city_name} at {lat:.6f}, {lon:.6f}")
            return lat, lon, city_name

        print(f"[PANORAMA] No panorama in {city_name}")

    # Запасной вариант
    print(f"[PANORAMA] All attempts failed, using Moscow center")
    result = find_panorama_in_moscow(max_attempts=10)

    if result:
        lat, lon = result
        return lat, lon, "Москва (запасной)"

    return 55.753544, 37.621202, "Москва"