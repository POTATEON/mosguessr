# routes/

Тут обработчики запросов. Разбиты на blueprint чтобы не мешать всё в кучу.

auth.py      - /auth/login, /auth/register, /auth/logout
game_api.py  - /api/game/new, /api/game/guess, /api/game/result
pages.py     - главная страница /, правила, about
profile.py   - /profile, /profile/history, /leaderboard

Если добавляешь новый урл - клади в подходящий blueprint. 
Не уверен куда - спроси в чате.