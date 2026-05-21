# database.py
import sqlite3
from datetime import datetime, timedelta

DB_NAME = "database.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Пользователи
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE NOT NULL,
            name TEXT,
            phone TEXT
        )
        """
    )

    # Рабочие дни
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS work_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,           -- YYYY-MM-DD
            is_closed INTEGER DEFAULT 0          -- 0/1
        )
        """
    )

    # Временные слоты
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS time_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_id INTEGER NOT NULL,
            time TEXT NOT NULL,                  -- HH:MM
            is_booked INTEGER DEFAULT 0,         -- 0/1
            user_id INTEGER,                     -- ссылка на users.id
            FOREIGN KEY(day_id) REFERENCES work_days(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    conn.commit()
    conn.close()


# ---------- Пользователи ----------

def get_or_create_user(tg_id: int, name: str | None = None, phone: str | None = None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    if row:
        user_id = row["id"]
        if name or phone:
            cur.execute(
                "UPDATE users SET name = COALESCE(?, name), phone = COALESCE(?, phone) WHERE id = ?",
                (name, phone, user_id)
            )
        conn.commit()
        conn.close()
        return user_id

    cur.execute(
        "INSERT INTO users (tg_id, name, phone) VALUES (?, ?, ?)",
        (tg_id, name, phone)
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def user_has_active_booking(tg_id: int) -> bool:
    """Проверка, что у пользователя нет активной записи в будущем."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ts.id
        FROM users u
        JOIN time_slots ts ON ts.user_id = u.id
        JOIN work_days wd ON wd.id = ts.day_id
        WHERE u.tg_id = ?
          AND ts.is_booked = 1
          AND DATE(wd.date) >= DATE('now')
        """,
        (tg_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


# ---------- Дни и слоты ----------

def add_work_day(date_str: str):
    """Добавить рабочий день (YYYY-MM-DD)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO work_days (date, is_closed) VALUES (?, 0)",
        (date_str,)
    )
    conn.commit()
    conn.close()


def close_day(date_str: str):
    """Полностью закрыть день (все слоты становятся недоступны)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE work_days SET is_closed = 1 WHERE date = ?", (date_str,))
    cur.execute(
        """
        UPDATE time_slots
        SET is_booked = 1
        WHERE day_id = (SELECT id FROM work_days WHERE date = ?)
        """,
        (date_str,)
    )
    conn.commit()
    conn.close()


def add_time_slot(date_str: str, time_str: str):
    """Добавить временной слот к дню."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM work_days WHERE date = ?", (date_str,))
    day = cur.fetchone()
    if not day:
        cur.execute(
            "INSERT INTO work_days (date, is_closed) VALUES (?, 0)",
            (date_str,)
        )
        day_id = cur.lastrowid
    else:
        day_id = day["id"]

    cur.execute(
        """
        INSERT INTO time_slots (day_id, time, is_booked, user_id)
        VALUES (?, ?, 0, NULL)
        """,
        (day_id, time_str)
    )

    conn.commit()
    conn.close()


def delete_time_slot(date_str: str, time_str: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM time_slots
        WHERE day_id = (SELECT id FROM work_days WHERE date = ?)
          AND time = ?
        """,
        (date_str, time_str)
    )
    conn.commit()
    conn.close()


def get_available_days_for_month() -> list[str]:
    """Список дат (YYYY-MM-DD) на месяц вперёд, где есть свободные слоты."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT wd.date
        FROM work_days wd
        JOIN time_slots ts ON ts.day_id = wd.id
        WHERE wd.is_closed = 0
          AND ts.is_booked = 0
          AND DATE(wd.date) BETWEEN DATE('now') AND DATE('now', '+30 days')
        ORDER BY wd.date
        """
    )
    rows = cur.fetchall()
    conn.close()
    return [r["date"] for r in rows]


def get_free_slots_for_date(date_str: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ts.id, ts.time
        FROM time_slots ts
        JOIN work_days wd ON wd.id = ts.day_id
        WHERE wd.date = ?
          AND wd.is_closed = 0
          AND ts.is_booked = 0
        ORDER BY ts.time
        """,
        (date_str,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def book_slot(slot_id: int, user_id: int) -> tuple[str, str] | None:
    """Забронировать слот. Возвращает (date, time) или None, если слота нет/занят."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT ts.id, ts.is_booked, ts.time, wd.date
        FROM time_slots ts
        JOIN work_days wd ON wd.id = ts.day_id
        WHERE ts.id = ? AND ts.is_booked = 0 AND wd.is_closed = 0
        """,
        (slot_id,)
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    cur.execute(
        "UPDATE time_slots SET is_booked = 1, user_id = ? WHERE id = ?",
        (user_id, slot_id)
    )
    conn.commit()
    conn.close()
    return row["date"], row["time"]


def cancel_booking_for_user(tg_id: int) -> tuple[str, str] | None:
    """Отменить одну активную запись пользователя (если есть)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ts.id, ts.time, wd.date
        FROM users u
        JOIN time_slots ts ON ts.user_id = u.id
        JOIN work_days wd ON wd.id = ts.day_id
        WHERE u.tg_id = ?
          AND ts.is_booked = 1
          AND DATE(wd.date) >= DATE('now')
        ORDER BY wd.date, ts.time
        LIMIT 1
        """,
        (tg_id,)
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    cur.execute(
        "UPDATE time_slots SET is_booked = 0, user_id = NULL WHERE id = ?",
        (row["id"],)
    )
    conn.commit()
    conn.close()
    return row["date"], row["time"]


def get_user_active_booking(tg_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ts.id, ts.time, wd.date
        FROM users u
        JOIN time_slots ts ON ts.user_id = u.id
        JOIN work_days wd ON wd.id = ts.day_id
        WHERE u.tg_id = ?
          AND ts.is_booked = 1
          AND DATE(wd.date) >= DATE('now')
        ORDER BY wd.date, ts.time
        LIMIT 1
        """,
        (tg_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row


def get_booking_by_slot_id(slot_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ts.id, ts.time, wd.date, u.tg_id
        FROM time_slots ts
        JOIN work_days wd ON wd.id = ts.day_id
        LEFT JOIN users u ON u.id = ts.user_id
        WHERE ts.id = ?
        """,
        (slot_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row


def get_all_future_bookings():
    """Для восстановления напоминаний при старте."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ts.id, ts.time, wd.date, u.tg_id
        FROM time_slots ts
        JOIN work_days wd ON wd.id = ts.day_id
        JOIN users u ON u.id = ts.user_id
        WHERE ts.is_booked = 1
          AND DATETIME(wd.date || ' ' || ts.time) > DATETIME('now')
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_schedule_for_date(date_str: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ts.time,
               ts.is_booked,
               u.name,
               u.phone
        FROM time_slots ts
        JOIN work_days wd ON wd.id = ts.day_id
        LEFT JOIN users u ON u.id = ts.user_id
        WHERE wd.date = ?
        ORDER BY ts.time
        """,
        (date_str,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows