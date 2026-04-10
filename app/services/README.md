# services/

Функции которые не зависят от Flask. Их можно вызывать откуда угодно.

geo_service.py    - haversine_distance(lat1, lng1, lat2, lng2) 
                  - calculate_score(distance_meters)
                  - get_random_location()

upload_service.py - save_panorama(file) -> путь к файлу
                  - validate_image(file) -> True/False
                  - delete_old_panorama(filename)

Не используй здесь request, session, url_for и прочие штуки Flask.
Только голая логика. Так легче тестировать и переиспользовать.