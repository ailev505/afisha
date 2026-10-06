import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "theater.db"


def get_connection():
    """Возвращает соединение с БД с доступом к колонкам по имени."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создаёт таблицы, если их нет."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS plays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            price INTEGER NOT NULL,
            seats_total INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            play_id INTEGER NOT NULL,
            seat_number INTEGER NOT NULL,
            order_number TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (play_id) REFERENCES plays(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def seed_db():
    """Заполняет БД тестовыми спектаклями, если она пустая."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM plays")
    count = cur.fetchone()[0]

    if count == 0:
        plays = [
            ("Вишнёвый сад", "2026-11-15T19:00", 800, 50),
            ("Гамлет", "2026-11-20T18:30", 1200, 50),
            ("Ревизор", "2026-11-25T19:00", 700, 50),
            ("Три сестры", "2026-12-01T18:00", 900, 50),
        ]
        cur.executemany(
            "INSERT INTO plays (title, date, price, seats_total) VALUES (?, ?, ?, ?)",
            plays
        )
        # Занятые места для наглядности
        cur.execute("INSERT INTO tickets (play_id, seat_number, order_number) VALUES (1, 3, 'SEED-1')")
        cur.execute("INSERT INTO tickets (play_id, seat_number, order_number) VALUES (1, 7, 'SEED-2')")
        cur.execute("INSERT INTO tickets (play_id, seat_number, order_number) VALUES (2, 1, 'SEED-3')")
        conn.commit()

    conn.close()


# ============================================================
# CRUD-операции
# ============================================================

def get_all_plays():
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.id, p.title, p.date, p.price, p.seats_total,
               (SELECT COUNT(*) FROM tickets t WHERE t.play_id = p.id) AS seats_taken
        FROM plays p
        ORDER BY p.date
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_play(play_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT p.id, p.title, p.date, p.price, p.seats_total,
               (SELECT COUNT(*) FROM tickets t WHERE t.play_id = p.id) AS seats_taken
        FROM plays p
        WHERE p.id = ?
    """, (play_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_taken_seats(play_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT seat_number FROM tickets WHERE play_id = ?",
        (play_id,)
    ).fetchall()
    conn.close()
    return [r["seat_number"] for r in rows]


def add_play(title, date, price, seats_total):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO plays (title, date, price, seats_total) VALUES (?, ?, ?, ?)",
        (title, date, price, seats_total)
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id


def delete_play(play_id):
    conn = get_connection()
    conn.execute("DELETE FROM tickets WHERE play_id = ?", (play_id,))
    conn.execute("DELETE FROM plays WHERE id = ?", (play_id,))
    conn.commit()
    conn.close()


def buy_tickets(play_id, seats, order_number):
    """Покупает билеты. Возвращает (успех, сообщение)."""
    conn = get_connection()
    cur = conn.cursor()

    # Проверка: не заняты ли места
    placeholders = ",".join("?" * len(seats))
    taken = cur.execute(
        f"SELECT seat_number FROM tickets WHERE play_id = ? AND seat_number IN ({placeholders})",
        (play_id, *seats)
    ).fetchall()

    if taken:
        conn.close()
        taken_nums = [t["seat_number"] for t in taken]
        return False, f"Места уже заняты: {taken_nums}"

    # Проверка: существует ли спектакль
    play = cur.execute("SELECT id FROM plays WHERE id = ?", (play_id,)).fetchone()
    if not play:
        conn.close()
        return False, "Спектакль не найден"

    # Записываем билеты
    for seat in seats:
        cur.execute(
            "INSERT INTO tickets (play_id, seat_number, order_number) VALUES (?, ?, ?)",
            (play_id, seat, order_number)
        )

    conn.commit()
    conn.close()
    return True, "Билеты успешно куплены"