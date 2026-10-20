"""
Главный файл сайта (Flask).
Здесь описаны все адреса (маршруты) сайта: какую страницу показать
и что сделать, когда браузер присылает данные.
"""
import os
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import database
from ai import ask_ai

app = Flask(__name__)
# Секретный ключ нужен, чтобы Flask мог хранить вход пользователя (сессию) в cookie
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

database.init_db()


def login_required(view):
    """Пускает на страницу только тех, кто вошёл. Остальных отправляет на /login."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.method == "POST":  # запрос из script.js — отвечаем JSON
                return jsonify(result=False, error="Сначала войдите в аккаунт"), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def current_user():
    return database.get_user_by_id(session["user_id"])


# ==================== Страницы ====================

@app.route("/")
def registration():
    if "user_id" in session:
        return redirect(url_for("lk"))
    return render_template("registration.html")


@app.route("/login")
def login():
    if "user_id" in session:
        return redirect(url_for("lk"))
    return render_template("login.html")


@app.route("/lk")
@login_required
def lk():
    return render_template("lk.html", user=current_user())


@app.route("/transactions")
@login_required
def transactions():
    user = current_user()
    return render_template(
        "transactions.html",
        user=user,
        transactions=database.get_transactions(user["id"]),
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==================== API (сюда шлёт данные script.js) ====================

@app.route("/user_register", methods=["POST"])
def user_register():
    req = request.get_json(silent=True) or {}
    first_name = req.get("first_name", "").strip()
    last_name = req.get("last_name", "").strip()
    email = req.get("email", "").strip().lower()
    password = req.get("password", "")

    if not first_name or not last_name or not email or not password:
        return jsonify(result=False, error="Заполните все поля")

    # Пароль не храним в открытом виде, только его хеш
    try:
        user_id = database.create_user(first_name, last_name, email, generate_password_hash(password))
    except Exception:
        return jsonify(result=False, error="Ошибка базы данных, попробуйте позже")
    if user_id is None:
        return jsonify(result=False, error="Пользователь с таким email уже есть")

    session["user_id"] = user_id  # сразу входим после регистрации
    return jsonify(result=True, id=user_id)


@app.route("/user_login", methods=["POST"])
def user_login():
    req = request.get_json(silent=True) or {}
    email = req.get("email", "").strip().lower()
    password = req.get("password", "")

    # Пытаемся выполнить SELECT из базы.
    # Если при выборке случилась ошибка — возвращаем браузеру false.
    try:
        user = database.get_user_by_email(email)
    except Exception:
        return jsonify(result=False, error="Ошибка базы данных, попробуйте позже")

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify(result=False, error="Неверный email или пароль")

    session["user_id"] = user["id"]
    return jsonify(result=True)


@app.route("/add_transaction", methods=["POST"])
@login_required
def add_transaction():
    req = request.get_json(silent=True) or {}
    kind = req.get("type")  # "deposit" (пополнение) или "withdraw" (списание)
    description = req.get("description", "").strip()

    try:
        amount = round(float(req.get("amount")), 2)
    except (TypeError, ValueError):
        return jsonify(result=False, error="Сумма должна быть числом")

    if amount <= 0:
        return jsonify(result=False, error="Сумма должна быть больше нуля")
    if kind not in ("deposit", "withdraw"):
        return jsonify(result=False, error="Неизвестный тип операции")

    if kind == "withdraw":
        amount = -amount
    if not description:
        description = "Пополнение" if amount > 0 else "Списание"

    new_balance = database.add_transaction(session["user_id"], amount, description)
    if new_balance is None:
        return jsonify(result=False, error="Недостаточно средств")
    return jsonify(result=True, balance=new_balance)


@app.route("/ask_ai", methods=["POST"])
@login_required
def ask_ai_route():
    question = (request.get_json(silent=True) or {}).get("question", "").strip()
    if not question:
        return jsonify(result=False, error="Напишите вопрос")

    user = current_user()
    # Подсказка для нейросети: кто с ней говорит и сколько у него денег
    system_prompt = (
        "Ты помощник в личном кабинете банковского приложения. "
        "Пользователь: %s %s, баланс: %.2f руб. "
        "Отвечай кратко и по-русски." % (user["first_name"], user["last_name"], user["balance"])
    )
    ok, text = ask_ai(question, system_prompt)
    if ok:
        return jsonify(result=True, answer=text)
    return jsonify(result=False, error=text)


if __name__ == "__main__":
    app.run(debug=True)
