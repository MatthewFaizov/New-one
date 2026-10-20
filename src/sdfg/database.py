"""
Работа с базой данных.

Используется SQLite: это база данных в одном файле (database.db),
которая встроена в Python. Ничего устанавливать не нужно,
файл создаётся сам при первом запуске.
"""
import os
import sqlite3

# Файл базы лежит рядом с этим файлом
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    # Чтобы строки из базы можно было читать как словарь: row["first_name"]
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создаёт таблицы, если их ещё нет. Вызывается при запуске сайта."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name    TEXT NOT NULL,
            last_name     TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            balance       REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL NOT NULL,      -- плюс = пополнение, минус = списание
            description TEXT,
            created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
    """)
    conn.commit()
    conn.close()


# ---------- Пользователи ----------

def create_user(first_name, last_name, email, password_hash):
    """Добавляет пользователя. Возвращает его id или None, если email уже занят."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO users (first_name, last_name, email, password_hash) VALUES (?, ?, ?, ?)",
            (first_name, last_name, email, password_hash),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        # Сработало UNIQUE у email: такой пользователь уже есть
        return None
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


# ---------- Транзакции ----------

def add_transaction(user_id, amount, description):
    """
    Создаёт транзакцию и меняет баланс.
    amount > 0 — пополнение, amount < 0 — списание.
    Возвращает новый баланс или None, если денег не хватает.
    """
    conn = get_connection()
    try:
        balance = conn.execute(
            "SELECT balance FROM users WHERE id = ?", (user_id,)
        ).fetchone()["balance"]

        new_balance = round(balance + amount, 2)
        if new_balance < 0:
            return None

        conn.execute(
            "INSERT INTO transactions (user_id, amount, description) VALUES (?, ?, ?)",
            (user_id, amount, description),
        )
        conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
        conn.commit()  # обе записи сохраняются вместе
        return new_balance
    finally:
        conn.close()


def get_transactions(user_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()
    return rows
