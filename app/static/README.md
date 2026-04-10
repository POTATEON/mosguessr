# static/

Всё что отдаётся браузеру как есть, без обработки сервером.

css/
    style.css - свои стили поверх Bootstrap, пиши сюда

js/
    game.js   - логика карты, отправка guess на сервер
    profile.js- графики статистики если будем делать

uploads/
    panoramas/ - сюда админ загружает панорамы через форму
                эту папку не коммитим, она в .gitignore

В шаблонах подключать так:
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
<img src="{{ url_for('static', filename='uploads/panoramas/red_square.jpg') }}">