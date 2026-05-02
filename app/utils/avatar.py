import hashlib
import os
from io import BytesIO
from typing import Tuple, Optional
from PIL import Image
from flask import current_app


def get_initials(name: str) -> str:
    """Получить инициалы из имени"""
    if not name:
        return "?"
    parts = name.split()
    if len(parts) > 1:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


def generate_color(string: str) -> Tuple[str, str]:
    """Генерирует уникальные цвета на основе строки"""
    hash_obj = hashlib.md5(string.encode())

    # Генерируем hue из хеша
    hue = int(hash_obj.hexdigest()[:8], 16) % 360

    # Преобразуем HSL в RGB для приятных цветов
    h = hue / 360
    s = 0.65  # насыщенность
    l = 0.55  # светлота

    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h * 6) % 2 - 1))
    m = l - c / 2

    if h < 1 / 6:
        r, g, b = c, x, 0
    elif h < 2 / 6:
        r, g, b = x, c, 0
    elif h < 3 / 6:
        r, g, b = 0, c, x
    elif h < 4 / 6:
        r, g, b = 0, x, c
    elif h < 5 / 6:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x

    bg_color = f"#{int((r + m) * 255):02x}{int((g + m) * 255):02x}{int((b + m) * 255):02x}"

    # Текст либо белый, либо темный в зависимости от яркости фона
    brightness = (int((r + m) * 255) * 299 + int((g + m) * 255) * 587 + int((b + m) * 255) * 114) / 1000
    text_color = "#ffffff" if brightness < 150 else "#333333"

    return bg_color, text_color


def generate_avatar_svg(name: str, size: int = 200) -> str:
    """Генерирует SVG аватар с инициалами"""
    initials = get_initials(name)
    bg_color, text_color = generate_color(name)

    # Вычисляем размер шрифта относительно размера аватарки и длины инициалов
    font_size = size // 2 if len(initials) == 2 else size // 3

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
        <defs>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@600&amp;display=swap');
            </style>
        </defs>
        <rect width="{size}" height="{size}" rx="{size // 6}" fill="{bg_color}"/>
        <text x="50%" y="50%" text-anchor="middle" dy="0.1em" 
              font-family="Inter, -apple-system, system-ui, sans-serif" 
              font-size="{font_size}px" font-weight="600" fill="{text_color}">
            {initials}
        </text>
    </svg>'''

    return svg


def process_uploaded_avatar(file_data, user_id: int, filename: str) -> Optional[str]:
    """
    Обрабатывает загруженный аватар:
    - Изменяет размер до 400x400
    - Сохраняет в static/avatars/
    - Возвращает URL сохраненного файла
    """
    try:
        # Создаем изображение из загруженных данных
        img = Image.open(BytesIO(file_data))

        # Конвертируем в RGB если нужно (для PNG с прозрачностью)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Создаем белый фон для прозрачных изображений
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Изменяем размер, сохраняя пропорции
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)

        # Генерируем уникальное имя файла
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
            file_ext = '.jpg'

        # Добавляем хеш для предотвращения кеширования
        import time
        unique_name = f"user_{user_id}_{int(time.time())}{file_ext}"

        # Сохраняем в папку static/avatars
        avatars_dir = os.path.join(current_app.static_folder, 'avatars')
        os.makedirs(avatars_dir, exist_ok=True)

        filepath = os.path.join(avatars_dir, unique_name)
        img.save(filepath, quality=85, optimize=True)

        # Возвращаем URL
        return f"/static/avatars/{unique_name}"

    except Exception as e:
        current_app.logger.error(f"Error processing avatar: {e}")
        return None


def delete_old_avatar(avatar_url: str):
    """Удаляет старый файл аватара"""
    if not avatar_url or not avatar_url.startswith('/static/avatars/'):
        return

    try:
        filepath = os.path.join(current_app.static_root, avatar_url.lstrip('/'))
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        current_app.logger.error(f"Error deleting old avatar: {e}")