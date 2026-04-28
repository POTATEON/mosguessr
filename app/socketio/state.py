"""Глобальное состояние игры"""
import threading

# =====================
# Классическая дуэль
# =====================
waiting_players = []              # [{user_id, name, sid}]
active_lobbies = {}               # {lobby_id: {...}}
duel_rooms = {}                   # {duel_id: {user_id: sid}}
round_timers = {}                 # {duel_id: {...}}
next_round_ready = {}             # {duel_id: set(user_ids)}
panorama_regeneration_count = {}  # {duel_id: count}

waiting_lock = threading.Lock()
panorama_regeneration_lock = threading.Lock()

# =====================
# Режим "Создатель"
# =====================
creator_locations = {}            # {duel_id: {user_id: {lat, lon}}}
creator_guesses = {}              # {duel_id: {user_id: {lat, lon}}}
creator_timers = {}               # {duel_id: timer_info}
creator_waiting_players = []
creator_waiting_lock = threading.Lock()