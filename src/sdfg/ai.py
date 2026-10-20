"""
Отправка запроса в нейросеть.

Поддерживаются два варианта:
  1) "gigachat" — GigaChat от Сбера (есть бесплатный тариф для физлиц).
  2) "openai"   — любой сервис с API в стиле OpenAI
                  (DeepSeek, OpenRouter, Ollama на своём компьютере и т.д.).

Для HTTP-запросов используется встроенный в Python модуль urllib,
поэтому ставить дополнительные библиотеки не нужно.
"""
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

# ===================== НАСТРОЙКИ =====================

# Какой сервис использовать: "gigachat" или "openai"
PROVIDER = os.environ.get("AI_PROVIDER", "gigachat")

# Ключ API. Можно вставить прямо сюда в кавычки
# или задать переменную окружения AI_API_KEY.
# Для GigaChat это «Ключ авторизации» из личного кабинета developers.sber.ru
API_KEY = ""

# --- GigaChat ---
GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
GIGACHAT_SCOPE = "GIGACHAT_API_PERS"  # для физлиц
GIGACHAT_MODEL = "GigaChat"

# --- OpenAI-совместимые сервисы ---
# Примеры:
#   DeepSeek: https://api.deepseek.com/chat/completions        модель deepseek-chat
#   Ollama:   http://localhost:11434/v1/chat/completions       модель llama3.2 (ключ не нужен)
OPENAI_API_URL = os.environ.get("AI_API_URL", "")
OPENAI_MODEL = os.environ.get("AI_MODEL", "")

# =====================================================

TIMEOUT = 60  # секунд ждём ответа

# Токен GigaChat живёт 30 минут, поэтому запоминаем его и не запрашиваем каждый раз
_gigachat_token = {"value": None, "expires_at": 0}


def _get_key():
    return API_KEY or os.environ.get("AI_API_KEY", "")


def _post_json(url, data, headers, ssl_context=None):
    """Отправляет POST-запрос и возвращает ответ сервера как словарь."""
    body = data if isinstance(data, bytes) else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=ssl_context) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _gigachat_ssl_context():
    # У серверов Сбера сертификат от «Минцифры», которому многие компьютеры
    # не доверяют. Поэтому проверку сертификата для GigaChat отключаем.
    # Для учебного проекта это нормально, для настоящего — так делать не стоит.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _gigachat_access_token():
    now_ms = time.time() * 1000
    if _gigachat_token["value"] and now_ms < _gigachat_token["expires_at"] - 60_000:
        return _gigachat_token["value"]

    result = _post_json(
        GIGACHAT_AUTH_URL,
        urllib.parse.urlencode({"scope": GIGACHAT_SCOPE}).encode("utf-8"),
        {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": "Basic " + _get_key(),
        },
        ssl_context=_gigachat_ssl_context(),
    )
    _gigachat_token["value"] = result["access_token"]
    _gigachat_token["expires_at"] = result["expires_at"]
    return result["access_token"]


def _ask_gigachat(messages):
    token = _gigachat_access_token()
    result = _post_json(
        GIGACHAT_API_URL,
        {"model": GIGACHAT_MODEL, "messages": messages},
        {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer " + token,
        },
        ssl_context=_gigachat_ssl_context(),
    )
    return result["choices"][0]["message"]["content"]


def _ask_openai_compatible(messages):
    headers = {"Content-Type": "application/json"}
    if _get_key():
        headers["Authorization"] = "Bearer " + _get_key()
    result = _post_json(
        OPENAI_API_URL,
        {"model": OPENAI_MODEL, "messages": messages},
        headers,
    )
    return result["choices"][0]["message"]["content"]


def ask_ai(question, system_prompt=""):
    """
    Главная функция: отправляет вопрос в нейросеть.
    Возвращает пару (успех, текст): (True, ответ) или (False, описание ошибки).
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": question})

    try:
        if PROVIDER == "gigachat":
            if not _get_key():
                return False, "Не задан ключ GigaChat. Вставь его в API_KEY в файле ai.py."
            return True, _ask_gigachat(messages)

        if PROVIDER == "openai":
            if not OPENAI_API_URL or not OPENAI_MODEL:
                return False, "Не заданы OPENAI_API_URL и OPENAI_MODEL в файле ai.py."
            return True, _ask_openai_compatible(messages)

        return False, "Неизвестный PROVIDER в ai.py: " + PROVIDER

    except urllib.error.HTTPError as e:
        details = e.read().decode("utf-8", errors="replace")[:300]
        if e.code in (401, 403):
            return False, "Нейросеть отклонила ключ (ошибка %s). Проверь API_KEY." % e.code
        return False, "Нейросеть вернула ошибку %s: %s" % (e.code, details)
    except urllib.error.URLError as e:
        return False, "Не удалось подключиться к нейросети: %s" % e.reason
    except (KeyError, IndexError, ValueError):
        return False, "Нейросеть прислала ответ в неожиданном формате."
    except Exception as e:  # таймаут и прочие неожиданности
        return False, "Ошибка при запросе к нейросети: %s" % e
