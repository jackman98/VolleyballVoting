import sqlite3

def connect_with_fk(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")  # Увімкнення
    return conn

# Ініціалізація бази даних
def init_db():
    conn = connect_with_fk("volleyball_bot.db")
    cursor = conn.cursor()

    # Таблиця для даних гри
    cursor.execute('''CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            date TEXT,
            time TEXT,
            location TEXT,
            FOREIGN KEY (chat_id) REFERENCES chats (id)
        )''')

    # Таблиця для учасників
    cursor.execute('''CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY,
            game_id INTEGER,
            name TEXT,
            status TEXT, -- "confirmed" або "declined",
            in_queue INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE
        )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY,  -- chat_id як унікальний ідентифікатор
            name TEXT
        )''')

    conn.commit()
    conn.close()

# Створити гру
def create_game(chat_id, date, time, location):
    conn = connect_with_fk("volleyball_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO games (chat_id, date, time, location) VALUES (?, ?, ?, ?)", (chat_id, date, time, location))
    conn.commit()
    conn.close()

def remove_game(game_id):
    conn = connect_with_fk("volleyball_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()

# Отримати список всіх ігор
def get_all_games():
    conn = connect_with_fk("volleyball_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, time, location FROM games")
    games = cursor.fetchall()
    conn.close()
    return games

# Отримати гру за ID
def get_game_by_id(game_id):
    conn = connect_with_fk("volleyball_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, date, time, location FROM games WHERE id = ?", (game_id,))
    game = cursor.fetchone()
    conn.close()
    return game

# Отримати останню гру
def get_latest_game():
    conn = connect_with_fk("volleyball_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, chat_id, date, time, location FROM games ORDER BY id DESC LIMIT 1")
    game = cursor.fetchone()
    conn.close()
    return game

# Додавання гравця
def add_player(user_id, name, game_id, status, in_queue=0):
    conn = connect_with_fk("volleyball_bot.db")
    cursor = conn.cursor()
    try:
        # Перевіряємо, чи існує гравець
        cursor.execute("SELECT id FROM players WHERE game_id = ? AND id = ?", (game_id, user_id))
        player = cursor.fetchone()

        if player:
            # Якщо гравець існує, оновлюємо його статус
            cursor.execute("UPDATE players SET status = ?, in_queue = ?, created_at = CURRENT_TIMESTAMP WHERE game_id = ? AND id = ?", (status, in_queue, game_id, user_id))
            print(f"Статус гравця '{name}' оновлено на '{status}'.")
        else:
            # Якщо гравця немає, додаємо його
            cursor.execute("INSERT INTO players (id, name, game_id, status, in_queue, created_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", (user_id, name, game_id, status, in_queue))
            print(f"Гравець '{name}' доданий зі статусом '{status}'.")

        conn.commit()
    except sqlite3.Error as e:
        print(f"Помилка під час роботи з базою даних: {e}")
    finally:
        conn.close()

# Видалення гравця
def remove_player(game_id, name):
    conn = connect_with_fk("volleyball_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM players WHERE game_id = ? AND name = ?", (game_id, name))
    conn.commit()
    conn.close()

# Отримання списку гравців
def get_players_for_game(game_id):
    conn = connect_with_fk("volleyball_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, status 
        FROM players 
        WHERE game_id = ?
        ORDER BY created_at ASC
    ''', (game_id,))
    players = cursor.fetchall()
    conn.close()
    return players

def get_confirmed_players_for_game(game_id):
    conn = connect_with_fk('volleyball_bot.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, name, status
        FROM players
        WHERE status = 'confirmed' AND game_id = ?
        ORDER BY created_at ASC
    ''', (game_id,))

    confirmed_players = cursor.fetchall()
    conn.close()
    return confirmed_players

def get_declined_players_for_game(game_id):
    conn = connect_with_fk('volleyball_bot.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, name, status
        FROM players
        WHERE status = 'declined' AND game_id = ?
        ORDER BY created_at ASC
    ''', (game_id,))

    confirmed_players = cursor.fetchall()
    conn.close()
    return confirmed_players


# Отримання черги
def get_queue(game_id):
    conn = connect_with_fk("volleyball_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, created_at FROM players WHERE game_id = ? AND in_queue = 1 ORDER BY created_at ASC", (game_id,))
    queue = [row[0] for row in cursor.fetchall()]
    conn.close()
    return queue

# Переміщення з черги
def move_from_queue(game_id):
    conn = connect_with_fk("volleyball_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, created_at FROM players WHERE game_id = ? AND in_queue = 1 AND status = 'confirmed' ORDER BY created_at ASC LIMIT 1", (game_id,))
    next_in_queue = cursor.fetchone()

    if next_in_queue:
        cursor.execute(
            "UPDATE players SET status = ?, in_queue = 0, created_at = CURRENT_TIMESTAMP WHERE game_id = ? AND id = ?",
            (next_in_queue[3], game_id, next_in_queue[2]))

        conn.commit()

    conn.close()
    return next_in_queue[0] if next_in_queue else None

def save_chat(chat_id, name):
    conn = connect_with_fk("volleyball_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO chats (id, name)
        VALUES (?, ?)
    ''', (chat_id, name))
    conn.commit()
    conn.close()

def get_all_chats():
    conn = connect_with_fk("volleyball_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM chats")
    chats = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    conn.close()
    return chats
