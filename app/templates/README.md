# templates/

HTML шаблоны. Все наследуются от base.html.

base.html - шапка, подвал, подключение Bootstrap, сюда не лезем без нужды

auth/
    login.html    - форма входа
    register.html - форма регистрации

game/
    play.html     - страница с панорамой и картой, тут вся игра

profile/
    profile.html    - личный кабинет игрока
    leaderboard.html- топ игроков

admin/
    upload_locations.html - форма для загрузки новых панорам (только админ)

Если меняешь вёрстку - сначала смотри base.html, там уже есть блоки content и scripts.