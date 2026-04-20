from app.utils.geo import get_random_city, calculate_score, haversine

# Здесь можно добавить дополнительную бизнес-логику,
# но основные функции уже вынесены в utils.geo.
# Для единообразия переэкспортируем:
__all__ = ['get_random_city', 'calculate_score', 'haversine']