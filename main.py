from __future__ import annotations
import asyncio
import csv
import hashlib
import html
import io
import json
import logging
import os
import random
import signal
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


APP_NAME = "VESTO"
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://fast-vesto-smart-wealth.base44.app").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "9109995015:AAFNF37UN_ECeJb0CBWOKqrRC6DEVVrWKdI").strip()
BASE44_API_URL = os.getenv("BASE44_API_URL", "https://fast-vesto-smart-wealth.base44.app/api").rstrip("/")
BASE44_API_TOKEN = os.getenv("BASE44_API_TOKEN", "b44u_67f11577a8ab23febb1d542bc1970c57c75caf9b9dc5869ec802e6449a6a9880").strip()
_base44_telegram_id = os.getenv("BASE44_TELEGRAM_ID", "6355289079").strip()
BASE44_TELEGRAM_ID = int(_base44_telegram_id) if _base44_telegram_id.isdigit() else None
DATABASE_PATH = os.getenv("VESTO_DATABASE", "vesto.sqlite3")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in {"1", "true", "yes", "on"}
ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "6355289079,1037433069,536196775").split(",")
    if value.strip().isdigit()
}
API_ROOT = f"https://api.telegram.org/bot{BOT_TOKEN}"
DISCLAIMER = "Faqat ma’lumot uchun. Kafolatlangan daromad emas. Bu moliyaviy maslahat emas."
DISCLAIMER_EN = "For information only. No guaranteed returns. This is not financial advice."
DISCLAIMER_RU = "Только для информации. Доход не гарантирован. Это не финансовая рекомендация."
MAX_MESSAGE_LENGTH = 3900
MARKET_INSTRUMENTS = (
    ("SOL-USD", "Solana", 138.70, 0.8, "crypto"),
    ("ETH-USD", "Ethereum", 3176.33, 11.7, "crypto"),
    ("BTC-USD", "Bitcoin", 64728.64, 9.8, "crypto"),
    ("GLD", "SPDR Gold Shares", 190.98, -7.0, "etf"),
    ("QQQ", "Invesco Nasdaq 100 ETF", 426.50, -0.1, "etf"),
    ("VTI", "Vanguard Total Market ETF", 256.95, 2.8, "etf"),
    ("VOO", "Vanguard S&P 500 ETF", 493.16, 7.4, "etf"),
    ("TSLA", "Tesla Inc.", 230.67, 3.9, "stock"),
    ("AMZN", "Amazon.com", 192.96, 3.4, "stock"),
    ("MSFT", "Microsoft Corp.", 396.79, 5.4, "stock"),
    ("AAPL", "Apple Inc.", 221.51, 8.5, "stock"),
    ("NVDA", "NVIDIA Corp.", 130.16, 0.6, "stock"),
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("vesto")

LANGS = {
    "uz": {
        "choose_lang": "Tilni tanlang:",
        "welcome": "Salom, {name}. VESTO’ga xush kelibsiz.\n\n"
                   "Bu — demo moliyaviy boshqaruv yordamchisi. Raqamlar simulyatsiya qilingan.",
        "menu": "Kerakli bo‘limni tanlang:",
        "open_app": "🚀 VESTO ilovasini ochish",
        "wealth": "💰 Boylik",
        "health": "❤️ Salomatlik",
        "accounts": "🏦 Hisoblar",
        "expenses": "🧾 Xarajatlar",
        "portfolio": "📈 Portfel",
        "goals": "🎯 Maqsadlar",
        "markets": "🌍 Bozor",
        "ai": "✦ Vesto AI",
        "autopilot": "⚙️ Autopilot",
        "family": "👨‍👩‍👧 Oila",
        "giving": "🎁 Xayriya",
        "reports": "📊 Hisobotlar",
        "plans": "💎 Tarif",
        "notifications": "🔔 Bildirishnomalar",
        "settings": "⚙️ Sozlamalar",
        "feedback": "💬 Aloqa / Feedback",
        "back": "⬅️ Menyu",
        "demo": "DEMO",
        "warning": "Faqat ma’lumot uchun. Kafolatlangan daromad emas. Bu moliyaviy maslahat emas.",
        "unknown": "Bu amalni tushunmadim. Menyudan bo‘lim tanlang yoki /help yuboring.",
        "cancelled": "Amal bekor qilindi.",
        "invalid_amount": "Summani musbat raqam sifatida yuboring. Bekor qilish uchun /cancel.",
        "goal_prompt": "Yangi maqsad nomini yuboring (masalan, Ta’til). Bekor qilish: /cancel.",
        "goal_amount_prompt": "Maqsad summasini {currency} da yuboring.",
        "contribute_prompt": "Qo‘shiladigan summani {currency} da yuboring.",
        "ai_prompt": "Savolingizni yozing. Masalan: “Eng katta xarajatim nima?”\n"
                      "Demo rejimida javoblar simulyatsiya qilingan ma’lumotlar asosida beriladi. /cancel — bekor qilish.",
        "not_configured": "Bot tokeni sozlanmagan. BOT_TOKEN muhit o‘zgaruvchisini kiriting.",
        "error": "Kechirasiz, amalni bajarishda xatolik yuz berdi. Birozdan so‘ng qayta urinib ko‘ring.",
        "saved": "Saqlandi.",
        "delete_prompt": "Barcha demo profilingiz va maqsadlaringiz o‘chiriladi. Tasdiqlaysizmi?",
        "deleted": "Ma’lumotlaringiz o‘chirildi. /start orqali qayta boshlang.",
        "autopilot_confirm": "Bu faqat virtual paper rejadagi harakat. Haqiqiy pul ishlatilmaydi.\n"
                             "Davom ettirishni tasdiqlaysizmi?",
        "paper_done": "Virtual paper amal bajarildi. Haqiqiy buyurtma yuborilmadi.",
        "on": "Yoqilgan",
        "off": "O‘chirilgan",
        "day": "Kunlik",
        "hour": "Soatlik",
        "not_found": "Bo‘lim topilmadi.",
    },
    "ru": {
        "choose_lang": "Выберите язык:",
        "welcome": "Здравствуйте, {name}. Добро пожаловать в VESTO.\n\n"
                   "Это демонстрационный финансовый помощник. Данные симулированы.",
        "menu": "Выберите раздел:",
        "open_app": "🚀 Открыть приложение VESTO",
        "wealth": "💰 Капитал",
        "health": "❤️ Финансовое здоровье",
        "accounts": "🏦 Счета",
        "expenses": "🧾 Расходы",
        "portfolio": "📈 Портфель",
        "goals": "🎯 Цели",
        "markets": "🌍 Рынок",
        "ai": "✦ Vesto AI",
        "autopilot": "⚙️ Автопилот",
        "family": "👨‍👩‍👧 Семья",
        "giving": "🎁 Благотворительность",
        "reports": "📊 Отчёты",
        "plans": "💎 Тариф",
        "notifications": "🔔 Уведомления",
        "settings": "⚙️ Настройки",
        "feedback": "💬 Связь / Feedback",
        "back": "⬅️ Меню",
        "demo": "ДЕМО",
        "warning": "Только для информации. Доход не гарантирован. Это не финансовая рекомендация.",
        "unknown": "Не удалось распознать действие. Выберите раздел или отправьте /help.",
        "cancelled": "Действие отменено.",
        "invalid_amount": "Введите положительное число. Для отмены отправьте /cancel.",
        "goal_prompt": "Отправьте название цели (например, Отпуск). Отмена: /cancel.",
        "goal_amount_prompt": "Отправьте сумму цели в {currency}.",
        "contribute_prompt": "Отправьте сумму пополнения в {currency}.",
        "ai_prompt": "Напишите вопрос, например: «Какие расходы самые крупные?»\n"
                     "Ответы в демо основаны на симулированных данных. /cancel — отмена.",
        "not_configured": "Токен бота не настроен. Укажите переменную окружения BOT_TOKEN.",
        "error": "Не удалось выполнить действие. Повторите попытку позже.",
        "saved": "Сохранено.",
        "delete_prompt": "Будут удалены ваш демопрофиль и цели. Подтвердить?",
        "deleted": "Данные удалены. Отправьте /start, чтобы начать заново.",
        "autopilot_confirm": "Это только виртуальный план paper trading. Реальные деньги не используются.\n"
                             "Подтвердить?",
        "paper_done": "Виртуальное действие выполнено. Реальный ордер не отправлялся.",
        "on": "Включено",
        "off": "Выключено",
        "day": "Ежедневно",
        "hour": "Ежечасно",
        "not_found": "Раздел не найден.",
    },
    "en": {
        "choose_lang": "Choose a language:",
        "welcome": "Hello, {name}. Welcome to VESTO.\n\n"
                   "This is a demo financial assistant. Figures are simulated.",
        "menu": "Choose a section:",
        "open_app": "🚀 Open VESTO app",
        "wealth": "💰 Wealth",
        "health": "❤️ Financial health",
        "accounts": "🏦 Accounts",
        "expenses": "🧾 Expenses",
        "portfolio": "📈 Portfolio",
        "goals": "🎯 Goals",
        "markets": "🌍 Markets",
        "ai": "✦ Vesto AI",
        "autopilot": "⚙️ Autopilot",
        "family": "👨‍👩‍👧 Family",
        "giving": "🎁 Giving",
        "reports": "📊 Reports",
        "plans": "💎 Plan",
        "notifications": "🔔 Notifications",
        "settings": "⚙️ Settings",
        "feedback": "💬 Contact / Feedback",
        "back": "⬅️ Menu",
        "demo": "DEMO",
        "warning": "For information only. No guaranteed returns. This is not financial advice.",
        "unknown": "I didn't recognize that. Choose a section or send /help.",
        "cancelled": "Action cancelled.",
        "invalid_amount": "Send a positive number. Send /cancel to stop.",
        "goal_prompt": "Send a goal name (for example, Holiday). Cancel: /cancel.",
        "goal_amount_prompt": "Send the goal amount in {currency}.",
        "contribute_prompt": "Send the contribution amount in {currency}.",
        "ai_prompt": "Ask a question, e.g. “What are my biggest expenses?”\n"
                     "Demo answers use simulated data. Send /cancel to stop.",
        "not_configured": "The bot token is not configured. Set the BOT_TOKEN environment variable.",
        "error": "Sorry, that action failed. Please try again shortly.",
        "saved": "Saved.",
        "delete_prompt": "Your demo profile and goals will be deleted. Confirm?",
        "deleted": "Your data was deleted. Send /start to begin again.",
        "autopilot_confirm": "This is a virtual paper-trading plan only. No real money is used.\n"
                             "Confirm to continue?",
        "paper_done": "Virtual paper action completed. No real order was submitted.",
        "on": "On",
        "off": "Off",
        "day": "Daily",
        "hour": "Hourly",
        "not_found": "Section not found.",
    },
}

MENU_KEYS = (
    "wealth", "health", "accounts", "expenses", "portfolio", "goals", "markets",
    "ai", "autopilot", "family", "giving", "reports", "plans", "notifications", "settings",
)
MENU_TEXT_TO_KEY: dict[str, str] = {}
for _language, _strings in LANGS.items():
    for _key in MENU_KEYS:
        MENU_TEXT_TO_KEY[_strings[_key]] = _key
    MENU_TEXT_TO_KEY[_strings["back"]] = "menu"
    MENU_TEXT_TO_KEY[_strings["open_app"]] = "app"


class Store:
    """Small SQLite persistence layer; all user data is scoped by Telegram ID."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'uz',
                currency TEXT NOT NULL DEFAULT 'USD',
                timezone TEXT NOT NULL DEFAULT 'Asia/Tashkent',
                risk_profile TEXT NOT NULL DEFAULT 'balanced',
                plan TEXT NOT NULL DEFAULT 'FREE',
                notify_frequency TEXT NOT NULL DEFAULT 'off',
                notify_time TEXT NOT NULL DEFAULT '09:00',
                last_notified REAL NOT NULL DEFAULT 0,
                accounts_connected INTEGER NOT NULL DEFAULT 1,
                autopilot_state TEXT NOT NULL DEFAULT 'stopped',
                muted_until REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                target REAL NOT NULL,
                current REAL NOT NULL DEFAULT 0,
                due_days INTEGER NOT NULL DEFAULT 365,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS paper_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
                state TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
                amount REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_goals_user ON goals(user_id);
            CREATE INDEX IF NOT EXISTS idx_paper_user ON paper_runs(user_id, created_at);
            """
        )
        self.db.commit()

    def user(self, user_id: int) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM users WHERE tg_id=?", (user_id,)).fetchone()

    def ensure_user(self, user_id: int, language: str = "uz") -> sqlite3.Row:
        self.db.execute(
            "INSERT OR IGNORE INTO users(tg_id,language,created_at) VALUES(?,?,?)",
            (user_id, language if language in LANGS else "uz", utc_now()),
        )
        self.db.commit()
        if self.db.execute("SELECT COUNT(*) FROM goals WHERE user_id=?", (user_id,)).fetchone()[0] == 0:
            rng = random.Random(seed_for(user_id))
            names = {
                "uz": [("Zaxira jamg‘arma", 18_000, 6_200), ("Sayohat", 4_500, 1_800), ("Avtomobil", 22_000, 7_000)],
                "ru": [("Резерв", 18_000, 6_200), ("Путешествие", 4_500, 1_800), ("Автомобиль", 22_000, 7_000)],
                "en": [("Emergency fund", 18_000, 6_200), ("Travel", 4_500, 1_800), ("Car", 22_000, 7_000)],
            }
            for name, target, current in names.get(language, names["uz"]):
                self.db.execute(
                    "INSERT INTO goals(user_id,name,target,current,due_days,created_at) VALUES(?,?,?,?,?,?)",
                    (user_id, name, target + rng.randrange(-1000, 1001), current, rng.choice((180, 365, 540)), utc_now()),
                )
            self.db.commit()
        return self.user(user_id)  # type: ignore[return-value]

    def set_value(self, user_id: int, field: str, value: Any) -> None:
        allowed = {"language", "currency", "timezone", "risk_profile", "plan", "notify_frequency",
                   "notify_time", "last_notified", "accounts_connected", "autopilot_state", "muted_until"}
        if field not in allowed:
            raise ValueError("Unsupported user setting")
        self.db.execute(f"UPDATE users SET {field}=? WHERE tg_id=?", (value, user_id))
        self.db.commit()

    def goals(self, user_id: int) -> list[sqlite3.Row]:
        return list(self.db.execute("SELECT * FROM goals WHERE user_id=? ORDER BY id", (user_id,)).fetchall())

    def add_goal(self, user_id: int, name: str, target: float) -> None:
        self.db.execute(
            "INSERT INTO goals(user_id,name,target,current,due_days,created_at) VALUES(?,?,?,0,365,?)",
            (user_id, name[:80], target, utc_now()),
        )
        self.db.commit()

    def contribute(self, user_id: int, goal_id: int, amount: float) -> bool:
        cursor = self.db.execute(
            "UPDATE goals SET current=current+? WHERE id=? AND user_id=?",
            (amount, goal_id, user_id),
        )
        self.db.commit()
        return cursor.rowcount == 1

    def delete_user(self, user_id: int) -> None:
        self.db.execute("DELETE FROM users WHERE tg_id=?", (user_id,))
        self.db.commit()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def seed_for(user_id: int) -> int:
    return int.from_bytes(hashlib.sha256(f"vest:{user_id}".encode()).digest()[:8], "big")


def money(amount: float, currency: str) -> str:
    if currency == "UZS":
        return f"{amount:,.0f} UZS".replace(",", " ")
    return f"${amount:,.2f}"


def display_money(usd_amount: float, currency: str) -> str:
    """Demo balances are stored in USD; convert only for display."""
    return money(usd_amount * 12_500 if currency == "UZS" else usd_amount, currency)


def parse_user_amount(text: str, currency: str) -> float:
    value = float(text.replace(",", "").replace(" ", ""))
    return value / 12_500 if currency == "UZS" else value


def demo_data(user_id: int) -> dict[str, Any]:
    rng = random.Random(seed_for(user_id))
    wealth = rng.randint(72_000, 245_000)
    accounts = [
        ("Everyday account", "USD", wealth * 0.20),
        ("Savings", "USD", wealth * 0.38),
        ("Main card", "UZS", wealth * 0.16 * 12_500),
    ]
    positions = [
        ("VTI · ETF", "ETF", 0.31), ("MSFT · Equity", "Equity", 0.27),
        ("AAPL · Equity", "Equity", 0.14), ("BND · Bond ETF", "ETF", 0.10),
        ("BTC · Crypto", "Crypto", 0.08), ("Deposit", "Deposit", 0.10),
    ]
    return {
        "wealth": wealth,
        "change_pct": round(rng.uniform(-1.3, 2.4), 1),
        "health": rng.randint(58, 84),
        "risk": rng.randint(38, 72),
        "opportunity": rng.randint(45, 76),
        "accounts": accounts,
        "positions": positions,
        "food": rng.randint(260, 640),
        "transport": rng.randint(70, 190),
        "subscriptions": rng.randint(20, 85),
        "unusual": rng.randint(280, 1100),
        "top_asset": max(positions, key=lambda x: x[2]),
    }


def t(user: sqlite3.Row, key: str, **kwargs: Any) -> str:
    language = user["language"] if user and user["language"] in LANGS else "uz"
    return LANGS[language][key].format(**kwargs)


def app_url(screen: str = "home", **params: str) -> str:
    separator = "&" if "?" in MINI_APP_URL else "?"
    return f"{MINI_APP_URL}{separator}{urllib.parse.urlencode({'screen': screen, **params})}"


def button(text: str, callback: str) -> dict[str, str]:
    return {"text": text, "callback_data": callback[:64]}


def inline_markup(user: sqlite3.Row, rows: list[list[dict[str, Any]]], screen: str = "home") -> dict[str, Any]:
    rows = [list(row) for row in rows]
    rows.append([{"text": t(user, "open_app"), "web_app": {"url": app_url(screen)}}])
    rows.append([button(t(user, "back"), "nav:menu")])
    return {"inline_keyboard": rows}


def menu_markup(user: sqlite3.Row, more: bool = False) -> dict[str, Any]:
    strings = LANGS[user["language"]]
    if more:
        rows = [
            [button(strings["health"], "nav:health") , button(strings["accounts"], "nav:accounts")],
            [button(strings["expenses"], "nav:expenses"), button(strings["markets"], "nav:markets")],
            [button(strings["family"], "nav:family"), button(strings["giving"], "nav:giving")],
            [button(strings["reports"], "nav:reports"), button(strings["plans"], "nav:plans")],
            [button(strings["autopilot"], "nav:autopilot")],
            [button(strings["back"] + " — " + ("Asosiy" if user["language"] == "uz" else "Главное" if user["language"] == "ru" else "Main"), "nav:menu")],
        ]
    else:
        rows = [
            [{"text": strings["open_app"], "web_app": {"url": app_url()}}],
            [button(strings["wealth"], "nav:wealth"), button(strings["portfolio"], "nav:portfolio")],
            [button(strings["goals"], "nav:goals"), button(strings["ai"], "nav:ai")],
            [button(strings["notifications"], "nav:notifications"), button(strings["settings"], "nav:settings")],
            [button(("➕ Boshqa bo‘limlar" if user["language"] == "uz" else "➕ Другие разделы" if user["language"] == "ru" else "➕ More sections"), "nav:menu_more")],
        ]
    return {"inline_keyboard": rows}


def reply_markup(user: sqlite3.Row) -> dict[str, Any]:
    strings = LANGS[user["language"]]
    rows: list[list[dict[str, Any]]] = [
        [{"text": strings["open_app"], "web_app": {"url": app_url()}}],
        [{"text": strings["wealth"]}, {"text": strings["portfolio"]}],
        [{"text": strings["goals"]}, {"text": strings["ai"]}],
        [{"text": strings["notifications"]}, {"text": strings["settings"]}],
    ]
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


class Telegram:
    def __init__(self, token: str) -> None:
        self.token = token
        self.api = f"https://api.telegram.org/bot{token}/"

    async def call(self, method: str, payload: dict[str, Any] | None = None, timeout: int = 40) -> Any:
        def request() -> Any:
            encoded = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                self.api + method,
                data=encoded,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    result = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                body = error.read().decode("utf-8", errors="replace")
                try:
                    detail = json.loads(body)
                except json.JSONDecodeError:
                    detail = {}
                if error.code == 429:
                    raise RetryAfter(float(detail.get("parameters", {}).get("retry_after", 2))) from error
                raise TelegramError(f"Telegram HTTP {error.code}: {detail.get('description', body[:200])}") from error
            except urllib.error.URLError as error:
                raise TelegramError(f"Telegram network error: {error.reason}") from error
            if not result.get("ok"):
                parameters = result.get("parameters", {})
                if "retry_after" in parameters:
                    raise RetryAfter(float(parameters["retry_after"]))
                raise TelegramError(str(result.get("description", "Telegram API error")))
            return result.get("result")

        return await asyncio.to_thread(request)

    async def send(self, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None,
                   parse_mode: str = "HTML", reply_to: int | None = None) -> Any:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text[:MAX_MESSAGE_LENGTH],
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if reply_to:
            payload["reply_to_message_id"] = reply_to
        return await self.call("sendMessage", payload)

    async def edit(self, chat_id: int, message_id: int, text: str,
                   markup: dict[str, Any] | None = None) -> Any:
        payload: dict[str, Any] = {
            "chat_id": chat_id, "message_id": message_id, "text": text[:MAX_MESSAGE_LENGTH],
            "parse_mode": "HTML", "disable_web_page_preview": True,
        }
        if markup:
            payload["reply_markup"] = markup
        return await self.call("editMessageText", payload)

    async def answer_callback(self, callback_id: str, text: str = "") -> None:
        try:
            await self.call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text[:180]})
        except TelegramError:
            log.debug("Callback answer failed")

    async def send_csv(self, chat_id: int, filename: str, content: str) -> Any:
        def request() -> Any:
            boundary = "----VestoBoundary" + str(int(time.time() * 1000))
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'
                "Content-Type: text/csv; charset=utf-8\r\n\r\n"
            ).encode("utf-8") + b"\xef\xbb\xbf" + content.encode("utf-8") + f"\r\n--{boundary}--\r\n".encode()
            req = urllib.request.Request(
                self.api + "sendDocument", data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            )
            with urllib.request.urlopen(req, timeout=40) as response:
                result = json.loads(response.read().decode("utf-8"))
            if not result.get("ok"):
                raise TelegramError(str(result.get("description", "Document upload failed")))
            return result["result"]
        return await asyncio.to_thread(request)


class TelegramError(Exception):
    pass


class Base44Error(Exception):
    pass


class Base44Client:
    """Authenticated client for the VESTO entities documented in the OpenAPI file."""

    def __init__(self, token: str, api_url: str) -> None:
        self.token = token
        self.api_url = api_url

    async def request(self, method: str, path: str, body: Any = None) -> Any:
        def send_request() -> Any:
            url = f"{self.api_url}/{path.lstrip('/')}"
            data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
            if data is not None:
                headers["Content-Type"] = "application/json"
            request = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    raw = response.read()
            except urllib.error.HTTPError as error:
                raise Base44Error(f"Base44 API returned HTTP {error.code}") from error
            except urllib.error.URLError as error:
                raise Base44Error("Base44 API connection failed") from error
            if not raw:
                return None
            try:
                return json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise Base44Error("Base44 API returned invalid JSON") from error

        return await asyncio.to_thread(send_request)

    async def list_entities(self, entity: str, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        parameters: dict[str, str] = {"limit": "100"}
        if query:
            parameters["q"] = json.dumps(query, separators=(",", ":"), ensure_ascii=False)
        path = f"entities/{urllib.parse.quote(entity)}?{urllib.parse.urlencode(parameters)}"
        result = await self.request("GET", path)
        if not isinstance(result, list):
            raise Base44Error(f"Base44 API returned an invalid {entity} list")
        return [row for row in result if isinstance(row, dict)]

    async def create_entities(self, entity: str, rows: list[dict[str, Any]]) -> None:
        if rows:
            await self.request("POST", f"entities/{urllib.parse.quote(entity)}/bulk", rows)

    async def create_entity(self, entity: str, row: dict[str, Any]) -> dict[str, Any]:
        result = await self.request("POST", f"entities/{urllib.parse.quote(entity)}", row)
        if not isinstance(result, dict):
            raise Base44Error(f"Base44 API did not return the created {entity}")
        return result

    async def update_entity(self, entity: str, record_id: str, row: dict[str, Any]) -> dict[str, Any]:
        path = f"entities/{urllib.parse.quote(entity)}/{urllib.parse.quote(record_id)}"
        result = await self.request("PUT", path, row)
        if not isinstance(result, dict):
            raise Base44Error(f"Base44 API did not return the updated {entity}")
        return result

    async def delete_entity(self, entity: str, record_id: str) -> None:
        path = f"entities/{urllib.parse.quote(entity)}/{urllib.parse.quote(record_id)}"
        await self.request("DELETE", path)


class RetryAfter(TelegramError):
    def __init__(self, seconds: float) -> None:
        super().__init__(f"Rate limited for {seconds}s")
        self.seconds = seconds


class VestoBot:
    def __init__(self, token: str) -> None:
        self.tg = Telegram(token)
        self.store = Store(DATABASE_PATH)
        self.base44 = Base44Client(BASE44_API_TOKEN, BASE44_API_URL) if BASE44_API_TOKEN else None
        self.base44_owner_id = BASE44_TELEGRAM_ID
        self.base44_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self.market_quote_cache: dict[str, tuple[float, float, float, str, str]] = {}
        self.base44_seeded = False
        self.base44_problem = False
        self.offset = 0
        self.pending: dict[int, dict[str, Any]] = {}
        self.stop_event = asyncio.Event()

    def user(self, user_id: int, telegram_language: str = "uz") -> sqlite3.Row:
        language = telegram_language[:2].lower()
        return self.store.ensure_user(user_id, language if language in LANGS else "uz")

    async def ensure_base44_demo(self, user: sqlite3.Row) -> None:
        if not self.base44 or self.base44_seeded:
            return

        chat_id = str(user["tg_id"])
        settings_rows = await self.base44.list_entities("VestoSettings", {"telegram_chat_id": chat_id})
        if not settings_rows:
            await self.base44.create_entity("VestoSettings", {
                "language": user["language"],
                "currency": user["currency"],
                "plan": user["plan"].lower(),
                "timezone": user["timezone"],
                "notify_frequency": user["notify_frequency"],
                "notify_time": user["notify_time"],
                "quiet_start": "23:00",
                "quiet_end": "07:00",
                "categories": {"wealth": True, "portfolio": True, "expenses": True, "goals": True},
                "thresholds": {"wealth_change_pct": 1.0, "concentration_pct": 30},
                "hide_amounts": False,
                "risk_profile": user["risk_profile"],
                "onboarding_done": True,
                "telegram_chat_id": chat_id,
                "telegram_linked": True,
            })
        else:
            remote_settings = settings_rows[0]
            for field in ("language", "currency", "timezone", "notify_frequency", "notify_time", "risk_profile"):
                if remote_settings.get(field) is not None:
                    self.store.set_value(user["tg_id"], field, remote_settings[field])
            if remote_settings.get("plan"):
                self.store.set_value(user["tg_id"], "plan", str(remote_settings["plan"]).upper())

        data = demo_data(user["tg_id"])
        account_rows = await self.base44.list_entities("VestoAccount")
        if not account_rows:
            await self.base44.create_entities("VestoAccount", [
                {"name": name, "kind": kind, "currency": currency, "balance": round(balance, 2),
                 "mask": f"•••• {str(user['tg_id'])[-4:]}", "connected": True}
                for (name, currency, balance), kind in zip(
                    data["accounts"],
                    ("bank", "deposit", "card"),
                )
            ])

        transaction_rows = await self.base44.list_entities("VestoTransaction")
        if not transaction_rows:
            rng = random.Random(seed_for(user["tg_id"]) + 4)
            categories = ("oziq-ovqat", "transport", "ijara", "obunalar", "kongilochar", "sogliq", "xayriya")
            merchants = {
                "oziq-ovqat": "Market",
                "transport": "Transport",
                "ijara": "Rent",
                "obunalar": "Subscription",
                "kongilochar": "Entertainment",
                "sogliq": "Pharmacy",
                "xayriya": "Donation",
            }
            rows = []
            for index in range(24):
                category = categories[index % len(categories)]
                anomaly = index in {5, 17}
                occurred = datetime.now(timezone.utc) - timedelta(days=rng.randrange(1, 90))
                rows.append({
                    "account_name": "Everyday account",
                    "merchant": merchants[category],
                    "category": category,
                    "amount": round(rng.uniform(350, 2400) if anomaly else rng.uniform(8, 180), 2),
                    "currency": "USD",
                    "occurred_at": occurred.isoformat(timespec="seconds"),
                    "is_anomaly": anomaly,
                    "is_subscription": category == "obunalar" and index % 2 == 0,
                })
            await self.base44.create_entities("VestoTransaction", rows)

        holding_rows = await self.base44.list_entities("VestoHolding")
        if not holding_rows:
            samples = (
                ("VTI", "Total market ETF", "etf", 275.0, 0.30),
                ("MSFT", "Microsoft", "stock", 420.0, 0.25),
                ("AAPL", "Apple", "stock", 220.0, 0.15),
                ("BND", "Bond ETF", "etf", 72.0, 0.10),
                ("BTC", "Bitcoin", "crypto", 67000.0, 0.10),
                ("DEP", "Term deposit", "deposit", 1.0, 0.10),
            )
            await self.base44.create_entities("VestoHolding", [
                {"symbol": symbol, "name": name, "asset_class": asset_class,
                 "quantity": round(data["wealth"] * 0.26 * weight / price, 6), "price": price,
                 "avg_cost": price * 0.96, "currency": "USD"}
                for symbol, name, asset_class, price, weight in samples
            ])

        goal_rows = await self.base44.list_entities("VestoGoal")
        if not goal_rows:
            local_goals = self.store.goals(user["tg_id"])
            await self.base44.create_entities("VestoGoal", [
                {"name": goal["name"], "target_amount": goal["target"],
                 "current_amount": goal["current"],
                 "target_date": (datetime.now(timezone.utc) + timedelta(days=goal["due_days"])).date().isoformat(),
                 "monthly_contribution": round(max(0, goal["target"] - goal["current"]) /
                                               max(goal["due_days"] / 30, 1), 2),
                 "icon": icon}
                for goal, icon in zip(local_goals, ("shield", "plane", "car"))
            ])

        market_rows = await self.base44.list_entities("VestoMarket")
        if not market_rows:
            await self.base44.create_entities("VestoMarket", [
                {"symbol": symbol, "name": name, "asset_class": asset_class,
                 "price": price, "change_pct": change_pct,
                 "history": [round(price * (0.985 + i * 0.003), 2) for i in range(10)]}
                for symbol, name, price, change_pct, asset_class in MARKET_INSTRUMENTS
            ])

        watch_rows = await self.base44.list_entities("VestoWatch")
        if not watch_rows:
            await self.base44.create_entities("VestoWatch", [
                {"symbol": symbol} for symbol, _, _, _, _ in MARKET_INSTRUMENTS
            ])
        insight_rows = await self.base44.list_entities("VestoInsight")
        if not insight_rows:
            await self.base44.create_entities("VestoInsight", [
                {
                    "kind": "concentration",
                    "severity": "mid",
                    "title": "Portfolio concentration",
                    "body": "Demo insight: review the largest holding and diversification.",
                    "dismissed": False,
                },
                {
                    "kind": "spending",
                    "severity": "low",
                    "title": "Unusual expense",
                    "body": "Demo insight: a simulated transaction is marked for review.",
                    "dismissed": False,
                },
            ])
        self.base44_cache.clear()
        self.base44_seeded = True
        self.base44_problem = False

    async def base44_entities(self, entity: str) -> list[dict[str, Any]] | None:
        if not self.base44:
            return None
        cached = self.base44_cache.get(entity)
        if cached and time.monotonic() - cached[0] < 20:
            return cached[1]
        rows = await self.base44.list_entities(entity)
        self.base44_cache[entity] = (time.monotonic(), rows)
        return rows

    async def fetch_market_quote(self, symbol: str) -> tuple[float, float, str, str] | None:
        cached = self.market_quote_cache.get(symbol)
        if cached and time.monotonic() - cached[0] < 30:
            return cached[1], cached[2], cached[3], cached[4]

        def request_quote() -> tuple[float, float, str, str]:
            url = (
                "https://query1.finance.yahoo.com/v8/finance/chart/"
                f"{urllib.parse.quote(symbol, safe='-')}?range=1d&interval=1m"
            )
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 VESTO bot market quote", "Accept": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
            chart = payload.get("chart", {})
            if chart.get("error"):
                raise ValueError("Quote provider rejected the symbol")
            result = chart["result"][0]
            meta = result["meta"]
            price = meta.get("regularMarketPrice")
            if not isinstance(price, (int, float)):
                closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
                price = next((value for value in reversed(closes) if isinstance(value, (int, float))), None)
            previous = meta.get("chartPreviousClose") or meta.get("previousClose")
            if not isinstance(price, (int, float)) or not isinstance(previous, (int, float)) or previous <= 0:
                raise ValueError("Quote provider returned incomplete price data")
            change_pct = (float(price) / float(previous) - 1) * 100
            timestamp = meta.get("regularMarketTime")
            quoted_at = (
                datetime.fromtimestamp(float(timestamp), timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                if timestamp else "time unavailable"
            )
            return float(price), change_pct, str(meta.get("currency", "USD")), quoted_at

        try:
            quote = await asyncio.to_thread(request_quote)
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            ValueError,
            KeyError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            log.warning("Market quote unavailable for %s: %s", symbol, type(error).__name__)
            return None
        self.market_quote_cache[symbol] = (time.monotonic(), *quote)
        return quote

    async def update_base44_settings(self, user_id: int, changes: dict[str, Any]) -> None:
        if not self.base44:
            return
        rows = await self.base44.list_entities("VestoSettings", {"telegram_chat_id": str(user_id)})
        if not rows or not rows[0].get("id"):
            raise Base44Error("Base44 settings record is missing")
        current = rows[0]
        fields = (
            "language", "currency", "plan", "timezone", "notify_frequency", "notify_time",
            "quiet_start", "quiet_end", "categories", "thresholds", "hide_amounts",
            "risk_profile", "onboarding_done", "telegram_chat_id", "telegram_linked",
        )
        updated = {key: current[key] for key in fields if key in current}
        updated.update(changes)
        await self.base44.update_entity("VestoSettings", str(current["id"]), updated)
        self.base44_cache.pop("VestoSettings", None)

    async def save_base44_goal_contribution(self, goal_id: str, amount: float) -> None:
        if not self.base44:
            return
        goals = await self.base44.list_entities("VestoGoal")
        for goal in goals:
            if str(goal.get("id")) != goal_id:
                continue
            updated = {key: goal[key] for key in (
                "name", "target_amount", "current_amount", "target_date", "monthly_contribution", "icon"
            ) if key in goal}
            updated["current_amount"] = float(updated.get("current_amount", 0)) + amount
            await self.base44.update_entity("VestoGoal", goal_id, updated)
            self.base44_cache.pop("VestoGoal", None)
            return
        raise Base44Error("Requested demo goal was not found in Base44")

    async def delete_base44_data(self, user_id: int) -> None:
        if not self.base44:
            return
        entities = (
            "VestoAccount", "VestoTransaction", "VestoHolding", "VestoGoal", "VestoInsight",
            "VestoAutopilot", "VestoMarket", "VestoWatch", "VestoFamily", "VestoGiving",
            "VestoAiMessage",
        )
        for entity in entities:
            records = await self.base44.list_entities(entity)
            for record in records:
                if record.get("id"):
                    await self.base44.delete_entity(entity, str(record["id"]))
        settings = await self.base44.list_entities("VestoSettings", {"telegram_chat_id": str(user_id)})
        for record in settings:
            if record.get("id"):
                await self.base44.delete_entity("VestoSettings", str(record["id"]))
        self.base44_cache.clear()
        self.base44_seeded = False

    def section_text(
        self, user: sqlite3.Row, section: str, api_data: dict[str, list[dict[str, Any]]] | None = None
    ) -> tuple[str, list[list[dict[str, Any]]], str]:
        data = demo_data(user["tg_id"])
        api_data = api_data or {}
        currency = user["currency"]
        amount = lambda value: display_money(value, currency)
        demo = f" · <b>{html.escape(t(user, 'demo'))}</b>"
        rows: list[list[dict[str, Any]]] = []
        screen = section

        if section == "wealth":
            remote_accounts = api_data.get("VestoAccount")
            remote_holdings = api_data.get("VestoHolding")
            if remote_accounts is not None or remote_holdings is not None:
                account_total = sum(
                    float(row.get("balance", 0)) / 12_500 if row.get("currency") == "UZS"
                    else float(row.get("balance", 0))
                    for row in remote_accounts or [] if row.get("connected", True)
                )
                holding_total = sum(
                    float(row.get("quantity", 0)) * float(row.get("price", 0)) /
                    (12_500 if row.get("currency") == "UZS" else 1)
                    for row in remote_holdings or []
                )
                data["wealth"] = account_total + holding_total
            sign = "+" if data["change_pct"] >= 0 else ""
            text = (
                f"💰 <b>{'Umumiy boylik' if user['language']=='uz' else 'Общий капитал' if user['language']=='ru' else 'Total wealth'}</b>{demo}\n"
                f"<b>{amount(data['wealth'])}</b>\n"
                f"24 soat: {sign}{data['change_pct']}% · 3 hisob va investitsiya portfeli.\n\n"
                f"<b>Keyingi qadam:</b> maqsadlaringizni ko‘rib chiqing va xarajatlar limitini belgilang."
            )
            rows = [[button("🔍 " + ("Bu raqamni tushuntir" if user["language"] == "uz" else "Explain this number"), "explain:wealth")]]
        elif section == "health":
            score = data["health"]
            parts = (("Jamg‘arma", 78), ("Zaxira", 64), ("Diversifikatsiya", 55), ("Maqsadlar", 61))
            text = f"❤️ <b>Financial Health: {score}/100</b>{demo}\n\n" + "\n".join(
                f"• {name}: {value}/100" for name, value in parts
            ) + f"\n\n{html.escape(t(user, 'warning'))}"
            rows = [[button("🔍 " + ("Nega shunday?" if user["language"] == "uz" else "Explain"), "explain:health")]]
        elif section == "accounts":
            connected = bool(user["accounts_connected"])
            api_accounts = api_data.get("VestoAccount")
            account_rows = (
                [(str(row.get("name", "Account")), str(row.get("currency", "USD")),
                  float(row.get("balance", 0)))
                 for row in api_accounts or [] if row.get("connected", True)]
                if api_accounts is not None else (data["accounts"][:3] if connected else [])
            )
            text = f"🏦 <b>Hisoblar va kartalar</b>{demo}\n\n"
            if account_rows:
                text += "\n".join(f"• {html.escape(name)} · {money(value, cur)}" for name, cur, value in account_rows)
                text += "\n\nDemo hisoblarni ulash/uzish faqat illyustrativ, haqiqiy bankka ulanish yo‘q."
            else:
                text += "Hozir ulangan demo hisob yo‘q."
            rows = [[button("➖ Demo hisoblarni uzish" if connected else "➕ Demo hisoblarni ulash", "accounts:toggle")]]
        elif section == "expenses":
            api_transactions = api_data.get("VestoTransaction")
            if api_transactions is not None:
                totals: dict[str, float] = {}
                for transaction in api_transactions:
                    category = str(transaction.get("category", "boshqa"))
                    totals[category] = totals.get(category, 0) + float(transaction.get("amount", 0))
                data["food"] = totals.get("oziq-ovqat", 0)
                data["transport"] = totals.get("transport", 0)
                data["subscriptions"] = sum(
                    float(tx.get("amount", 0)) for tx in api_transactions if tx.get("is_subscription")
                )
                data["unusual"] = sum(
                    float(tx.get("amount", 0)) for tx in api_transactions if tx.get("is_anomaly")
                )
            api_insights = api_data.get("VestoInsight") or []
            text = (
                f"🧾 <b>Xarajatlar tahlili</b>{demo}\n\n"
                f"• Oziq-ovqat: {amount(data['food'])}\n"
                f"• Transport: {amount(data['transport'])}\n"
                f"• Obunalar: {amount(data['subscriptions'])}/oy\n"
                f"• G‘ayrioddiy xarajat: {amount(data['unusual'])}\n\n"
                "Bu oy/o‘tgan oy taqqoslash va noodatiy xarajatlar — demo hisob bo‘yicha."
            )
            if api_insights:
                text += "\n\n<b>VESTO tushunchalari:</b>\n" + "\n".join(
                    f"• {html.escape(str(item.get('title', 'Insight')))} — "
                    f"{html.escape(str(item.get('body', '')))}"
                    for item in api_insights if not item.get("dismissed")
                )
            rows = [[button("📅 Oy bo‘yicha", "nav:expenses")]]
        elif section == "portfolio":
            api_holdings = api_data.get("VestoHolding")
            positions = data["positions"]
            if api_holdings is not None:
                total_value = sum(
                    float(item.get("quantity", 0)) * float(item.get("price", 0)) for item in api_holdings
                )
                positions = [
                    (str(item.get("symbol", "Asset")), str(item.get("asset_class", "asset")),
                     (float(item.get("quantity", 0)) * float(item.get("price", 0)) / total_value)
                     if total_value > 0 else 0)
                    for item in api_holdings
                ]
            text = (
                f"📈 <b>Portfel</b>{demo}\n"
                f"Risk Score: <b>{data['risk']}/100</b> · Opportunity Score: <b>{data['opportunity']}/100</b>\n"
                "Confidence: O‘rta\n\n"
                + "\n".join(f"• {html.escape(name)} — {round(weight*100)}%" for name, _, weight in positions)
                + f"\n\nScenario Analysis: ssenariylar taxminiy diapazon, bashorat emas.\n\n{html.escape(t(user, 'warning'))}"
            )
            rows = [[button("🔍 Scenarios", "portfolio:scenario"), button("🔍 Explain", "explain:portfolio")]]
        elif section == "goals":
            api_goals = api_data.get("VestoGoal")
            goals = api_goals if api_goals is not None else self.store.goals(user["tg_id"])
            text = f"🎯 <b>Maqsadlar</b>{demo}\n\n"
            for index, goal in enumerate(goals, 1):
                current = float(goal.get("current_amount", goal.get("current", 0)))
                target = float(goal.get("target_amount", goal.get("target", 1)))
                progress = min(100, int(current / max(target, 1) * 100))
                text += f"{index}. <b>{html.escape(str(goal['name']))}</b> · {progress}%\n"
                text += f"   {amount(current)} / {amount(target)}\n"
                goal_id = str(goal.get("id", ""))
                if goal_id:
                    rows.append([button(f"➕ {index}-maqsadga qo‘shish", f"goal:add:{goal_id}")])
            rows.append([button("➕ Yangi maqsad", "goal:new")])
        elif section == "markets":
            text = f"🌍 <b>Bozor kuzatuvi</b>{demo}\n\n"
            api_markets = api_data.get("VestoMarket")
            api_by_symbol = {
                str(row.get("symbol", "")).upper(): row for row in api_markets or []
            }
            text += "Joriy ko‘rsatkichni ko‘rish va ilovada tahlil qilish uchun aktivni tanlang:\n"
            for symbol, name, reference_price, reference_change, asset_class in MARKET_INSTRUMENTS:
                quote = api_by_symbol.get(symbol, {})
                price = float(quote.get("price", reference_price))
                change = float(quote.get("change_pct", reference_change))
                text += f"\n• {html.escape(name)}: ${price:,.2f} · 24h {change:+.1f}%"
                rows.append([button(f"📊 {name} · {symbol}", f"market:{symbol}")])
            text += "\n\nNarxni tanlaganda jonli kotirovka olinadi; bozor manbasi kechikishi mumkin."
            watchlist = api_data.get("VestoWatch")
            if watchlist:
                text += "\nKuzatuv ro‘yxati: " + ", ".join(
                    html.escape(str(item.get("symbol", ""))) for item in watchlist
                )
            rows.append([button("⭐ Kuzatuv ro‘yxati", "markets:watch")])
        elif section == "ai":
            text = f"✦ <b>Vesto AI</b>{demo}\n\nSavolingizni yozing yoki tezkor savolni tanlang."
            rows = [
                [button("Nima o‘zgardi?", "ai:changed"), button("Eng katta xarajat?", "ai:expenses")],
                [button("Xavfim qancha?", "ai:risk"), button("Keyin nima qilay?", "ai:next")],
                [button("Maqsadimga yetamanmi?", "ai:goal")],
            ]
        elif section == "autopilot":
            api_runs = api_data.get("VestoAutopilot")
            state = str(api_runs[-1].get("status")) if api_runs else user["autopilot_state"]
            text = (
                f"⚙️ <b>Autopilot</b>{demo}\nHolat: <b>{html.escape(state)}</b>\n\n"
                "Tahlil va ijro faqat simulyatsiya/paper trading. Har qanday virtual ijro oldidan tasdiq so‘raladi.\n"
                f"{html.escape(t(user, 'warning'))}"
            )
            if state not in {"monitoring", "executing"}:
                rows.append([button("Tahlil qilish", "auto:analyze")])
            else:
                rows.append([button("⏸ To‘xtatish", "auto:stop")])
        elif section == "family":
            family = api_data.get("VestoFamily")
            text = f"👨‍👩‍👧 <b>Oila</b>{demo}\n\n"
            text += (f"API’da {len(family)} ta a’zo/invitation." if family is not None
                     else "Oilaviy ko‘rinish demo rejimida. Taklif havolasini ulashish uchun Mini App’dagi Oila bo‘limidan foydalaning.")
            rows = [[button("Oila bo‘limini ochish", "open:family")]]
        elif section == "giving":
            giving_rows = api_data.get("VestoGiving")
            donations = (
                sum(float(row.get("total_given", 0)) for row in giving_rows or [])
                if giving_rows is not None else
                self.store.db.execute("SELECT COALESCE(SUM(amount),0) FROM donations WHERE user_id=?",
                                      (user["tg_id"],)).fetchone()[0]
            )
            text = f"🎁 <b>Xayriya</b>{demo}\n\nDemo xayriya jami: {amount(donations)}.\nBu amal pul o‘tkazmaydi."
            rows = [[button("➕ Virtual xayriya qo‘shish", "giving:add")]]
        elif section == "reports":
            text = (
                f"📊 <b>Hisobot</b>{demo}\n\n"
                f"Boylik: {amount(data['wealth'])}\n"
                f"Financial Health: {data['health']}/100\n"
                f"Portfel Risk Score: {data['risk']}/100\n"
                f"Demo ma’lumotlar · {datetime.now().strftime('%Y-%m-%d')}"
            )
            rows = [[button("⬇️ CSV fayl yuborish", "report:csv")]]
        elif section == "plans":
            plans = [("FREE", "$0"), ("SMART", "$9.99"), ("INVESTOR", "$19.99"),
                     ("FAMILY", "$29.99"), ("PRO", "$49.99")]
            text = f"💎 <b>Tariflar</b>{demo}\nJoriy tarif: <b>{html.escape(user['plan'])}</b>\n\n"
            text += "\n".join(f"• {name} — {price}/oy" for name, price in plans)
            text += "\n\nDemo tarif tanlash haqiqiy to‘lov olmaydi."
            rows = [[button(f"Tanlash: {plan}", f"plan:{plan}") for plan in ("SMART", "INVESTOR")],
                    [button("FAMILY", "plan:FAMILY"), button("PRO", "plan:PRO")]]
        elif section == "notifications":
            frequency = user["notify_frequency"]
            api_settings = api_data.get("VestoSettings")
            if api_settings:
                frequency = api_settings[0].get("notify_frequency", frequency)
            choices = {"off": "Off", "hourly": "Soatlik", "daily": "Kunlik"}
            text = (
                f"🔔 <b>Bildirishnomalar</b>{demo}\n"
                f"Holat: <b>{choices.get(frequency, frequency)}</b>\n"
                f"Kunlik vaqt: {html.escape(api_settings[0].get('notify_time', user['notify_time']) if api_settings else user['notify_time'])} ({html.escape(user['timezone'])})\n"
                "Xulosa faqat VESTO demo raqamlariga asoslanadi."
            )
            rows = [[button("Off", "notify:off"), button("Soatlik", "notify:hourly"), button("Kunlik", "notify:daily")],
                    [button("Vaqtni 09:00 qilish", "notify:time")]]
        elif section == "settings":
            api_settings = api_data.get("VestoSettings")
            if api_settings:
                user_language = api_settings[0].get("language", user["language"])
                user_currency = api_settings[0].get("currency", user["currency"])
                user_timezone = api_settings[0].get("timezone", user["timezone"])
                user_risk = api_settings[0].get("risk_profile", user["risk_profile"])
                user_plan = str(api_settings[0].get("plan", user["plan"])).upper()
            else:
                user_language, user_currency = user["language"], user["currency"]
                user_timezone, user_risk, user_plan = user["timezone"], user["risk_profile"], user["plan"]
            text = (
                f"⚙️ <b>Sozlamalar</b>\nTil: {user_language} · Valyuta: {user_currency} · Tarif: {user_plan}\n"
                f"Vaqt zonasi: {user_timezone} · Xavf profili: {user_risk}\n"
                "Barcha bot raqamlari demo ma’lumotidir."
            )
            rows = [
                [button("O‘zbek", "lang:uz"), button("Русский", "lang:ru"), button("English", "lang:en")],
                [button("USD", "currency:USD"), button("UZS", "currency:UZS")],
                [button("🗑 Ma’lumotni o‘chirish", "data:delete")],
            ]
        else:
            return t(user, "not_found"), [], "home"
        return text, rows, screen

    async def show(self, chat_id: int, user: sqlite3.Row, section: str, message_id: int | None = None) -> None:
        if section == "menu":
            text = html.escape(t(user, "menu"))
            markup = menu_markup(user)
            if message_id:
                try:
                    await self.tg.edit(chat_id, message_id, text, markup)
                    return
                except TelegramError:
                    pass
            await self.tg.send(chat_id, text, reply_markup=markup, parse_mode="HTML")
            return
        if section == "menu_more":
            title = "Boshqa bo‘limlar:" if user["language"] == "uz" else "Другие разделы:" if user["language"] == "ru" else "More sections:"
            markup = menu_markup(user, more=True)
            if message_id:
                try:
                    await self.tg.edit(chat_id, message_id, title, markup)
                    return
                except TelegramError:
                    pass
            await self.tg.send(chat_id, title, reply_markup=markup)
            return
        api_data: dict[str, list[dict[str, Any]]] = {}
        api_error = False
        if self.base44:
            entities = {
                "wealth": ("VestoAccount", "VestoHolding"),
                "accounts": ("VestoAccount",),
                "expenses": ("VestoTransaction", "VestoInsight"),
                "portfolio": ("VestoHolding",),
                "goals": ("VestoGoal",),
                "markets": ("VestoMarket", "VestoWatch"),
                "autopilot": ("VestoAutopilot",),
                "family": ("VestoFamily",),
                "giving": ("VestoGiving",),
                "reports": ("VestoAccount", "VestoHolding", "VestoTransaction", "VestoGoal", "VestoInsight"),
                "plans": ("VestoSettings",),
                "notifications": ("VestoSettings",),
                "settings": ("VestoSettings",),
            }
            try:
                await self.ensure_base44_demo(user)
                for entity in entities.get(section, ()):
                    if entity == "VestoSettings":
                        api_data[entity] = await self.base44.list_entities(
                            entity, {"telegram_chat_id": str(user["tg_id"])}
                        )
                    else:
                        api_data[entity] = await self.base44_entities(entity) or []
                self.base44_problem = False
            except Base44Error:
                self.base44_problem = True
                api_error = True
                log.exception("Base44 integration request failed")
        text, rows, screen = self.section_text(user, section, api_data)
        if api_error:
            text += "\n\n⚠️ Base44 API bilan aloqa bo‘lmadi; hozir lokal DEMO ma’lumoti ko‘rsatilmoqda."
        markup = inline_markup(user, rows, screen)
        if message_id:
            try:
                await self.tg.edit(chat_id, message_id, text, markup)
                return
            except TelegramError as error:
                if "message is not modified" in str(error).lower():
                    return
                log.debug("Unable to edit section message: %s", error)
        await self.tg.send(chat_id, text, markup)

    async def start(self, message: dict[str, Any]) -> None:
        chat_id = message["chat"]["id"]
        sender = message["from"]
        user = self.user(sender["id"], sender.get("language_code", "uz"))
        args = (message.get("text") or "").split(maxsplit=1)
        if len(args) > 1 and args[1].startswith("app_"):
            await self.show(chat_id, user, args[1][4:])
            return
        name = html.escape(sender.get("first_name", ""))
        await self.tg.send(chat_id, t(user, "welcome", name=name), reply_markup=reply_markup(user))
        await self.show(chat_id, user, "menu")

    async def handle_message(self, message: dict[str, Any]) -> None:
        sender = message.get("from")
        if not sender or sender.get("is_bot"):
            return
        user_id = sender["id"]
        user = self.user(user_id, sender.get("language_code", "uz"))
        chat_id = message["chat"]["id"]
        text = (message.get("text") or "").strip()
        if not text:
            return
        if text.startswith("/"):
            command, _, argument = text.partition(" ")
            command = command.split("@", 1)[0].lower()
            if command in {"/start"}:
                await self.start(message)
            elif command in {"/menu"}:
                await self.show(chat_id, user, "menu")
            elif command == "/app":
                await self.tg.send(chat_id, "VESTO Mini App:", {"inline_keyboard": [[
                    {"text": t(user, "open_app"), "web_app": {"url": app_url()}}
                ]]})
            elif command == "/help":
                await self.tg.send(chat_id, "VESTO demo bot\n/start · /menu · /app · /digest_now · /demo · /id · /cancel")
            elif command == "/id":
                await self.tg.send(chat_id, f"Telegram ID: <code>{user_id}</code>", parse_mode="HTML")
            elif command == "/cancel":
                self.pending.pop(user_id, None)
                await self.tg.send(chat_id, t(user, "cancelled"))
            elif command == "/demo":
                await self.delete_base44_data(user_id)
                self.store.delete_user(user_id)
                user = self.user(user_id, user["language"])
                await self.tg.send(chat_id, t(user, "welcome", name=html.escape(sender.get("first_name", ""))),
                                   reply_markup=reply_markup(user))
                await self.show(chat_id, user, "wealth")
            elif command == "/digest_now":
                await self.send_digest(chat_id, user)
            elif command == "/simulate":
                if not DEMO_MODE and user_id not in ADMIN_IDS:
                    await self.tg.send(chat_id, "Admin ruxsati kerak.")
                else:
                    await self.tg.send(chat_id, f"🧪 DEMO simulyatsiya: portfelda sezilarli o‘zgarish aniqlandi.\n\n{html.escape(t(user, 'warning'))}")
            elif command == "/diag":
                if user_id not in ADMIN_IDS and user_id != self.base44_owner_id:
                    await self.tg.send(chat_id, "Bu buyruq faqat admin uchun.")
                else:
                    api_state = "yoqilmagan"
                    if self.base44:
                        api_state = "ulangan" if self.base44_seeded and not self.base44_problem else (
                            "xatolik" if self.base44_problem else "token sozlangan, hali tekshirilmagan"
                        )
                    await self.tg.send(
                        chat_id,
                        f"Demo rejim: {'faol' if DEMO_MODE else 'o‘chiq'}\n"
                        f"Base44 API: {api_state}\n"
                        f"API token: {'mavjud' if self.base44 else 'yo‘q'}\n"
                        "Telegram bot: polling\nMini App: sozlangan",
                    )
            elif command == "/notify":
                await self.show(chat_id, user, "notifications")
            else:
                await self.tg.send(chat_id, t(user, "unknown"))
            return

        current = self.pending.get(user_id)
        if current:
            try:
                await self.handle_pending(chat_id, user, text, current)
            except Base44Error:
                self.base44_problem = True
                log.exception("Base44 action failed for pending input")
                await self.tg.send(chat_id, "Base44 API bilan aloqa xatosi. So‘rovingiz saqlanmadi; qayta urinib ko‘ring.")
            return
        section = MENU_TEXT_TO_KEY.get(text)
        if section:
            if section == "app":
                await self.tg.send(chat_id, "VESTO Mini App:", {"inline_keyboard": [[
                    {"text": t(user, "open_app"), "web_app": {"url": app_url()}}
                ]]})
            elif section == "menu":
                await self.show(chat_id, user, "menu")
            elif section == "ai":
                await self.show(chat_id, user, "ai")
            else:
                await self.show(chat_id, user, section)
            return
        if text.casefold() in {"uz", "ru", "en"}:
            self.store.set_value(user_id, "language", text.casefold())
            user = self.store.user(user_id)
            await self.tg.send(chat_id, t(user, "saved"), reply_markup=reply_markup(user))
            await self.show(chat_id, user, "menu")
            return
        await self.answer_ai(chat_id, user, text)

    async def handle_pending(self, chat_id: int, user: sqlite3.Row, text: str, pending: dict[str, Any]) -> None:
        user_id = user["tg_id"]
        if pending["step"] == "goal_name":
            self.pending[user_id] = {"step": "goal_amount", "name": text[:80]}
            await self.tg.send(chat_id, t(user, "goal_amount_prompt", currency=user["currency"]))
            return
        if pending["step"] in {"goal_amount", "goal_contribute", "donation"}:
            try:
                amount = parse_user_amount(text, user["currency"])
                if amount <= 0 or amount > 1_000_000_000:
                    raise ValueError
            except ValueError:
                await self.tg.send(chat_id, t(user, "invalid_amount"))
                return
            if pending["step"] == "goal_amount":
                if self.base44:
                    await self.base44.create_entity("VestoGoal", {
                        "name": pending["name"][:80],
                        "target_amount": amount,
                        "current_amount": 0,
                        "target_date": (datetime.now(timezone.utc) + timedelta(days=365)).date().isoformat(),
                        "monthly_contribution": round(amount / 12, 2),
                        "icon": "shield",
                    })
                    self.base44_cache.pop("VestoGoal", None)
                self.store.add_goal(user_id, pending["name"], amount)
                result = "Maqsad yaratildi."
                screen = "goals"
            elif pending["step"] == "goal_contribute":
                if self.base44:
                    await self.save_base44_goal_contribution(str(pending["goal_id"]), amount)
                else:
                    if not self.store.contribute(user_id, int(pending["goal_id"]), amount):
                        await self.tg.send(chat_id, t(user, "error"))
                        self.pending.pop(user_id, None)
                        return
                result = "Maqsad demo tarzida to‘ldirildi."
                screen = "goals"
            else:
                if self.base44:
                    await self.base44.create_entity("VestoGiving", {
                        "cause": "VESTO demo charity",

                        "monthly_donation": amount,
                        "telegram_chat_id": str(user_id),
                    })
                    self.base44_cache.pop("VestoGiving", None)

                self.store.db.execute(
                    "INSERT INTO donations(user_id,amount,created_at) VALUES(?,?,?)",
                    (user_id, amount, utc_now()),
                )
                self.store.db.commit()
                result = "Virtual xayriya qayd etildi. Pul o‘tkazilmadi."
                screen = "giving"
            self.pending.pop(user_id, None)
            await self.tg.send(chat_id, f"✅ {result} [DEMO]", reply_markup=reply_markup(user))
            await self.show(chat_id, self.store.user(user_id), screen)

    async def answer_ai(self, chat_id: int, user: sqlite3.Row, query: str) -> None:
        q = query.casefold()
        data = demo_data(user["tg_id"])
        if any(word in q for word in ("xarajat", "expense", "расход")):
            answer = f"Demo tahlili: eng katta ko‘rsatilgan kategoriya oziq-ovqat — {money(data['food'], user['currency'])}. "
        elif any(word in q for word in ("risk", "хавф", "риск")):
            answer = f"Portfolio Risk Score: {data['risk']}/100 (demo baholash). "
        elif any(word in q for word in ("goal", "maqsad", "цель")):
            goals = self.store.goals(user["tg_id"])
            progress = int(goals[0]["current"] / max(goals[0]["target"], 1) * 100) if goals else 0
            answer = f"Birinchi maqsad progressi taxminan {progress}%. "
        elif any(word in q for word in ("o‘zg", "uzg", "change", "измен")):
            answer = f"Demo davrida boylik o‘zgarishi {data['change_pct']:+.1f}% sifatida simulyatsiya qilingan. "
        else:
            answer = "Ma’lumotlaringiz bo‘yicha aniqroq so‘rang: boylik, xarajatlar, Risk Score yoki maqsadlar. "
        warning = t(user, "warning")
        history_error = False
        if self.base44:
            try:
                await self.base44.create_entity("VestoAiMessage", {"role": "user", "text": query[:2000]})
                await self.base44.create_entity("VestoAiMessage", {"role": "assistant", "text": answer[:2000]})
            except Base44Error:
                self.base44_problem = True
                history_error = True
                log.exception("Unable to save demo AI conversation to Base44")
        history_notice = "\n\nSuhbat tarixi Base44 API’ga saqlanmadi." if history_error else ""
        await self.tg.send(
            chat_id,
            f"✦ <b>Vesto AI · DEMO</b>\n{html.escape(answer)}{html.escape(history_notice)}\n{html.escape(warning)}",
        )

    async def callback(self, query: dict[str, Any]) -> None:
        callback_id = query["id"]
        sender = query["from"]
        user = self.user(sender["id"], sender.get("language_code", "uz"))
        chat = query.get("message", {}).get("chat", {})
        chat_id = chat.get("id")
        message_id = query.get("message", {}).get("message_id")
        if not chat_id:
            await self.tg.answer_callback(callback_id)
            return
        data = query.get("data", "")
        try:
            await self.tg.answer_callback(callback_id)
            parts = data.split(":")
            if parts[0] == "nav":
                await self.show(chat_id, user, parts[1] if len(parts) > 1 else "menu", message_id)
            elif parts[0] == "open":
                await self.tg.send(chat_id, "Bo‘lim Mini App’da ochiladi:", {
                    "inline_keyboard": [[{"text": t(user, "open_app"), "web_app": {"url": app_url(parts[1])}}]]
                })
            elif parts[0] == "explain":
                await self.answer_ai(chat_id, user, "Nega bu raqam shunday?")
            elif parts[0] == "accounts":
                self.store.set_value(user["tg_id"], "accounts_connected", 0 if user["accounts_connected"] else 1)
                if self.base44:
                    accounts = await self.base44.list_entities("VestoAccount")
                    connected = bool(user["accounts_connected"])
                    for account in accounts:
                        if account.get("id"):
                            updated = {key: account[key] for key in ("name", "kind", "currency", "balance", "mask")
                                       if key in account}
                            updated["connected"] = not connected
                            await self.base44.update_entity("VestoAccount", str(account["id"]), updated)
                    self.base44_cache.pop("VestoAccount", None)
                await self.show(chat_id, self.store.user(user["tg_id"]), "accounts", message_id)
            elif parts[0] == "goal" and parts[1] == "new":
                self.pending[user["tg_id"]] = {"step": "goal_name"}
                await self.tg.send(chat_id, t(user, "goal_prompt"))
            elif parts[0] == "goal" and parts[1] == "add":
                goal_id = parts[2]
                self.pending[user["tg_id"]] = {"step": "goal_contribute", "goal_id": goal_id}
                await self.tg.send(chat_id, t(user, "contribute_prompt", currency=user["currency"]))
            elif parts[0] == "notify" and len(parts) > 1 and parts[1] == "time":
                self.store.set_value(user["tg_id"], "notify_time", "09:00")
                await self.update_base44_settings(user["tg_id"], {"notify_time": "09:00"})
                await self.show(chat_id, self.store.user(user["tg_id"]), "notifications", message_id)
            elif parts[0] == "notify":
                freq = parts[1]
                if freq in {"off", "hourly", "daily"}:
                    self.store.set_value(user["tg_id"], "notify_frequency", freq)
                    await self.update_base44_settings(user["tg_id"], {"notify_frequency": freq})
                    if freq == "daily":
                        self.store.set_value(user["tg_id"], "last_notified", 0)
                    await self.show(chat_id, self.store.user(user["tg_id"]), "notifications", message_id)
            elif parts[0] == "mute":
                hours = min(max(int(parts[1]), 1), 168)
                self.store.set_value(user["tg_id"], "muted_until", time.time() + hours * 3600)
                await self.tg.send(chat_id, f"Bildirishnomalar {hours} soatga jim qilindi.")
            elif parts[0] == "lang":
                if parts[1] in LANGS:
                    self.store.set_value(user["tg_id"], "language", parts[1])
                    await self.update_base44_settings(user["tg_id"], {"language": parts[1]})
                    await self.show(chat_id, self.store.user(user["tg_id"]), "settings", message_id)
            elif parts[0] == "currency":
                if parts[1] in {"USD", "UZS"}:
                    self.store.set_value(user["tg_id"], "currency", parts[1])
                    await self.update_base44_settings(user["tg_id"], {"currency": parts[1]})
                    await self.show(chat_id, self.store.user(user["tg_id"]), "settings", message_id)
            elif parts[0] == "auto" and parts[1] == "analyze":
                self.store.set_value(user["tg_id"], "autopilot_state", "awaiting_confirm")
                if self.base44:
                    await self.base44.create_entity("VestoAutopilot", {
                        "status": "awaiting_confirm",
                        "amount": 250,
                        "horizon_months": 12,
                        "risk_level": "balanced",
                        "allocations": [
                            {"symbol": "VTI", "percent": 60},
                            {"symbol": "BND", "percent": 40},
                        ],
                        "note": "Demo-only paper plan; confirmation is required.",
                    })
                    self.base44_cache.pop("VestoAutopilot", None)
                updated = self.store.user(user["tg_id"])
                text = (
                    "🧪 <b>Demo tahlil tayyor</b>\n"
                    "• Risk toleransi: balanslangan\n• Bir martalik demo limit: $250\n"
                    "• Reja: diversifikatsiyalangan virtual taqsimot\n"
                    f"{html.escape(t(updated, 'warning'))}\n\n{html.escape(t(updated, 'autopilot_confirm'))}"
                )
                markup = inline_markup(updated, [[button("✅ Tasdiqlash", "auto:confirm"),
                                                   button("❌ Rad etish", "auto:reject")]], "autopilot")
                await self.tg.edit(chat_id, message_id, text, markup)
            elif parts[0] == "auto" and parts[1] == "confirm":
                if user["autopilot_state"] != "awaiting_confirm":
                    await self.tg.send(chat_id, "Tasdiqlash uchun faol tahlil topilmadi.")
                else:
                    self.store.set_value(user["tg_id"], "autopilot_state", "monitoring")
                    self.store.db.execute(
                        "INSERT INTO paper_runs(user_id,state,amount,created_at) VALUES(?,?,?,?)",
                        (user["tg_id"], "paper_executed", 250, utc_now()),
                    )
                    self.store.db.commit()
                    if self.base44:
                        runs = await self.base44.list_entities("VestoAutopilot")
                        awaiting = next((run for run in reversed(runs)
                                         if run.get("status") == "awaiting_confirm" and run.get("id")), None)
                        if awaiting:
                            await self.base44.update_entity("VestoAutopilot", str(awaiting["id"]), {
                                "status": "monitoring",
                                "amount": awaiting.get("amount", 250),
                                "horizon_months": awaiting.get("horizon_months", 12),
                                "risk_level": awaiting.get("risk_level", "balanced"),
                                "allocations": awaiting.get("allocations", []),
                                "note": "Paper trading only; user confirmed demo plan.",
                                "executed_at": utc_now(),
                            })
                            self.base44_cache.pop("VestoAutopilot", None)
                    updated = self.store.user(user["tg_id"])
                    await self.tg.edit(chat_id, message_id, f"✅ {html.escape(t(updated, 'paper_done'))}\n[DEMO]")
                    await self.show(chat_id, updated, "autopilot")
            elif parts[0] == "auto" and parts[1] in {"reject", "stop"}:
                self.store.set_value(user["tg_id"], "autopilot_state", "stopped")
                if self.base44:
                    runs = await self.base44.list_entities("VestoAutopilot")
                    active = next((run for run in reversed(runs)
                                   if run.get("status") in {"awaiting_confirm", "monitoring", "paused"} and run.get("id")), None)
                    if active:
                        await self.base44.update_entity("VestoAutopilot", str(active["id"]), {
                            "status": "stopped",
                            "amount": active.get("amount", 0),
                            "horizon_months": active.get("horizon_months", 12),
                            "risk_level": active.get("risk_level", "balanced"),
                            "allocations": active.get("allocations", []),
                            "note": "Stopped by the user.",
                        })
                        self.base44_cache.pop("VestoAutopilot", None)
                await self.show(chat_id, self.store.user(user["tg_id"]), "autopilot", message_id)
            elif parts[0] == "portfolio":
                await self.tg.send(chat_id, "Scenario Analysis — taxminiy diapazon, bashorat emas. [DEMO]\n"
                                   + html.escape(t(user, "warning")))
            elif parts[0] == "market" and len(parts) > 1:
                symbol = parts[1].upper()
                instrument = next((item for item in MARKET_INSTRUMENTS if item[0] == symbol), None)
                if not instrument:
                    await self.tg.send(chat_id, "Bu instrument bozor ro‘yxatida yo‘q.")
                else:
                    _, name, reference_price, reference_change, _ = instrument
                    quote = await self.fetch_market_quote(symbol)
                    if quote:
                        price, change_pct, currency, quoted_at = quote
                        change_sign = "+" if change_pct >= 0 else ""
                        text = (
                            f"🌍 <b>{html.escape(name)} ({symbol})</b>\n"
                            f"So‘nggi kotirovka: <b>{html.escape(currency)} {price:,.2f}</b>\n"
                            f"24 soat: {change_sign}{change_pct:.2f}%\n"
                            f"Manba: Yahoo Finance · {html.escape(quoted_at)} · kechikishi mumkin.\n\n"
                            f"{html.escape(t(user, 'warning'))}"
                        )
                    else:
                        change_sign = "+" if reference_change >= 0 else ""
                        text = (
                            f"🌍 <b>{html.escape(name)} ({symbol})</b>\n"
                            "Jonli kotirovka hozircha olinmadi.\n"
                            f"Demo ma’lumotdagi so‘nggi ko‘rsatkich: <b>${reference_price:,.2f}</b> · "
                            f"{change_sign}{reference_change:.1f}% [DEMO]\n\n"
                            f"Manba: Yahoo Finance; kotirovka kechikishi mumkin.\n"
                            f"{html.escape(t(user, 'warning'))}"
                        )
                    markup = {
                        "inline_keyboard": [
                            [{
                                "text": "📊 Mini App’da tahlil qilish",
                                "web_app": {
                                    "url": app_url("markets", symbol=symbol, action="analysis")
                                },
                            }],
                            [button("⬅️ Bozor ro‘yxati", "nav:markets")],
                        ]
                    }
                    await self.tg.send(chat_id, text, markup)
            elif parts[0] == "ai":
                intent = {"changed": "Nima o‘zgardi?", "expenses": "Eng katta xarajatlarim?",
                          "risk": "Xavfim qancha?", "next": "Keyin nima qilay?",
                          "goal": "Maqsadimga yetamanmi?"}.get(parts[1], "Moliyaviy holatim")
                await self.answer_ai(chat_id, user, intent)
            elif parts[0] == "giving" and parts[1] == "add":
                self.pending[user["tg_id"]] = {"step": "donation"}
                await self.tg.send(chat_id, t(user, "contribute_prompt", currency=user["currency"]))
            elif parts[0] == "report" and parts[1] == "csv":
                await self.send_report(chat_id, user)
            elif parts[0] == "plan":
                plan = parts[1]
                if plan in {"SMART", "INVESTOR", "FAMILY", "PRO"}:
                    self.store.set_value(user["tg_id"], "plan", plan)
                    await self.update_base44_settings(user["tg_id"], {"plan": plan.lower()})
                    await self.tg.send(chat_id, f"Tarif demo rejimida {plan} ga o‘zgartirildi. To‘lov olinmadi.")
                    await self.show(chat_id, self.store.user(user["tg_id"]), "plans", message_id)
            elif parts[0] == "data" and parts[1] == "delete":
                await self.tg.send(chat_id, t(user, "delete_prompt"), {
                    "inline_keyboard": [[button("✅ O‘chirish", "data:confirm"), button("Bekor qilish", "nav:settings")]]
                })
            elif parts[0] == "data" and parts[1] == "confirm":
                await self.delete_base44_data(user["tg_id"])
                self.store.delete_user(user["tg_id"])
                self.pending.pop(user["tg_id"], None)
                await self.tg.send(chat_id, t(user, "deleted"), reply_markup={"remove_keyboard": True})
            elif parts[0] == "markets":
                await self.tg.send(chat_id, "Watchlist va price alert sozlamalari Mini App’da mavjud. Demo qiymatlar real emas.",
                                   {"inline_keyboard": [[{"text": t(user, "open_app"),
                                                          "web_app": {"url": app_url("markets")}}]]})
        except (ValueError, IndexError, sqlite3.Error) as error:
            log.warning("Invalid callback payload or storage error: %s", error)
            await self.tg.send(chat_id, t(user, "error"))
        except Base44Error:
            self.base44_problem = True
            log.exception("Base44 callback action failed")
            await self.tg.send(chat_id, "Base44 API bilan aloqa xatosi. Amal bajarilmadi; qayta urinib ko‘ring.")
        except TelegramError:
            log.exception("Telegram callback handling failed")
        except Exception:
            log.exception("Unexpected callback failure")
            await self.tg.send(chat_id, t(user, "error"))

    async def send_report(self, chat_id: int, user: sqlite3.Row) -> None:
        data = demo_data(user["tg_id"])
        rows = [
            ["Metric", "Value", "Mode"],
            ["Total wealth", data["wealth"], "DEMO"],
            ["Financial Health", data["health"], "DEMO"],
            ["Risk Score", data["risk"], "DEMO"],
            ["Opportunity Score", data["opportunity"], "DEMO"],
        ]
        if self.base44:
            try:
                accounts = await self.base44.list_entities("VestoAccount")
                holdings = await self.base44.list_entities("VestoHolding")
                goals = await self.base44.list_entities("VestoGoal")
                transactions = await self.base44.list_entities("VestoTransaction")
                total_accounts = sum(
                    float(row.get("balance", 0)) / (12_500 if row.get("currency") == "UZS" else 1)
                    for row in accounts if row.get("connected", True)
                )
                total_holdings = sum(
                    float(row.get("quantity", 0)) * float(row.get("price", 0)) for row in holdings
                )
                rows = [
                    ["Metric", "Value", "Mode"],
                    ["Total wealth (USD)", round(total_accounts + total_holdings, 2), "DEMO · Base44"],
                    ["Financial Health", data["health"], "DEMO estimate"],
                    ["Risk Score", data["risk"], "DEMO estimate"],
                    ["Opportunity Score", data["opportunity"], "DEMO estimate"],
                    ["Accounts", len(accounts), "DEMO · Base44"],
                    ["Holdings", len(holdings), "DEMO · Base44"],
                    ["Transactions", len(transactions), "DEMO · Base44"],
                ]
                rows.extend(
                    [["Goal", goal.get("name", ""), f"{goal.get('current_amount', 0)}/{goal.get('target_amount', 0)}"]
                     for goal in goals]
                )
            except Base44Error:
                self.base44_problem = True
                log.exception("Unable to load report data from Base44")
                rows.append(["API status", "Local demo fallback", "Base44 unavailable"])
        buffer = io.StringIO()
        csv.writer(buffer).writerows(rows)
        await self.tg.send_csv(chat_id, "vesto-demo-report.csv", buffer.getvalue())

    async def send_digest(self, chat_id: int, user: sqlite3.Row) -> None:
        data = demo_data(user["tg_id"])
        api_error = False
        if self.base44:
            try:
                await self.ensure_base44_demo(user)
                accounts = await self.base44_entities("VestoAccount") or []
                holdings = await self.base44_entities("VestoHolding") or []
                transactions = await self.base44_entities("VestoTransaction") or []
                account_total = sum(
                    float(row.get("balance", 0)) / (12_500 if row.get("currency") == "UZS" else 1)
                    for row in accounts if row.get("connected", True)
                )
                holding_total = sum(
                    float(row.get("quantity", 0)) * float(row.get("price", 0)) for row in holdings
                )
                data["wealth"] = account_total + holding_total
                data["food"] = sum(float(row.get("amount", 0)) for row in transactions
                                   if row.get("category") == "oziq-ovqat")
            except Base44Error:
                self.base44_problem = True
                api_error = True
                log.exception("Unable to load digest data from Base44")
        sign = "+" if data["change_pct"] >= 0 else ""
        text = (
            f"✦ <b>VESTO · Xulosa [DEMO]</b>\n"
            f"💰 Umumiy boylik: {display_money(data['wealth'], user['currency'])} · {sign}{data['change_pct']}%\n"
            f"📈 Risk Score: {data['risk']} · Opportunity Score: {data['opportunity']}\n"
            f"🧾 Xarajatlar: oziq-ovqat {display_money(data['food'], user['currency'])}\n\n"
            f"{html.escape(t(user, 'warning'))}"
        )
        if api_error:
            text += "\n\nBase44 API bilan aloqa bo‘lmadi; lokal demo qiymatlar ishlatildi."
        await self.tg.send(
            chat_id,
            text,
            inline_markup(
                user,
                [[button("🔍 Batafsil", "nav:wealth")], [button("🔕 Jim qilish (24 soat)", "mute:24")]],
                "home",
            ),
        )

    async def poll(self) -> None:
        while not self.stop_event.is_set():
            try:
                updates = await self.tg.call(
                    "getUpdates",
                    {"offset": self.offset, "timeout": 25,
                     "allowed_updates": ["message", "callback_query"]},
                    timeout=35,
                )
                for update in updates or []:
                    self.offset = max(self.offset, update["update_id"] + 1)
                    try:
                        if "message" in update:
                            await self.handle_message(update["message"])
                        elif "callback_query" in update:
                            await self.callback(update["callback_query"])
                    except RetryAfter as error:
                        log.warning("Rate limited; pausing %.1fs", error.seconds)
                        await asyncio.sleep(error.seconds)
                    except TelegramError as error:
                        log.warning("Update delivery failed: %s", error)
                    except Exception:
                        log.exception("Update handling failed")
            except RetryAfter as error:
                await asyncio.sleep(error.seconds)
            except TelegramError as error:
                log.warning("Polling failed: %s", error)
                await asyncio.sleep(3)

    async def notifications(self) -> None:
        while not self.stop_event.is_set():
            try:
                users = self.store.db.execute(
                    "SELECT * FROM users WHERE notify_frequency IN ('hourly','daily')"
                ).fetchall()
                now = time.time()
                for user in users:
                    if user["muted_until"] > now:
                        continue
                    interval = 3600 if user["notify_frequency"] == "hourly" else 86400
                    if now - user["last_notified"] < interval:
                        continue
                    if user["notify_frequency"] == "daily":
                        try:
                            local = datetime.now(ZoneInfo(user["timezone"]))
                        except (ZoneInfoNotFoundError, ValueError):
                            local = datetime.now(timezone.utc)
                        hour, minute = map(int, user["notify_time"].split(":"))
                        if local.hour != hour or local.minute > 2:
                            continue
                    try:
                        await self.send_digest(user["tg_id"], user)
                        self.store.set_value(user["tg_id"], "last_notified", now)
                        await asyncio.sleep(0.05)
                    except RetryAfter as error:
                        await asyncio.sleep(error.seconds)
                    except TelegramError as error:
                        if "blocked" in str(error).lower() or "deactivated" in str(error).lower():
                            self.store.delete_user(user["tg_id"])
                        else:
                            log.warning("Scheduled notification failed: %s", error)
            except Exception:
                log.exception("Notification scheduler iteration failed")
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=30)
            except asyncio.TimeoutError:
                pass

    async def configure(self) -> None:
        try:
            await self.tg.call("deleteWebhook", {"drop_pending_updates": False})
            commands = [
                {"command": "start", "description": "VESTO botni boshlash"},
                {"command": "menu", "description": "Asosiy menyu"},
                {"command": "app", "description": "VESTO Mini App"},
                {"command": "id", "description": "Telegram ID (API demo ulash uchun)"},
                {"command": "notify", "description": "Bildirishnoma sozlamalari"},
                {"command": "digest_now", "description": "Demo xulosani hozir olish"},
                {"command": "demo", "description": "Demo profilni tiklash"},
                {"command": "help", "description": "Yordam"},
            ]
            await self.tg.call("setMyCommands", {"commands": commands})
            await self.tg.call("setChatMenuButton", {
                "menu_button": {
                    "type": "web_app",
                    "text": "VESTO",
                    "web_app": {"url": app_url()},
                }
            })
        except TelegramError as error:
            log.warning("Bot menu setup failed: %s", error)

    async def run(self) -> None:
        await self.configure()
        log.info("VESTO bot started (demo=%s, Mini App URL configured)", DEMO_MODE)
        polling = asyncio.create_task(self.poll(), name="telegram-polling")
        scheduler = asyncio.create_task(self.notifications(), name="notification-scheduler")
        try:
            await asyncio.gather(polling, scheduler)
        except asyncio.CancelledError:
            pass
        finally:
            self.stop_event.set()
            polling.cancel()
            scheduler.cancel()
            await asyncio.gather(polling, scheduler, return_exceptions=True)
            self.store.db.close()


async def main() -> None:
    if not BOT_TOKEN:
        print("Set BOT_TOKEN before starting. Example (PowerShell):", file=sys.stderr)
        print('$env:BOT_TOKEN = "123456:your-token"; python .\\main.py', file=sys.stderr)
        raise SystemExit(2)
    if BASE44_API_TOKEN and BASE44_TELEGRAM_ID is None:
        print("Set BASE44_TELEGRAM_ID to the one Telegram account allowed to use the Base44 PAT.", file=sys.stderr)
        print("Use /id in the bot to find your Telegram ID; never paste tokens into chat.", file=sys.stderr)
        raise SystemExit(2)
    bot = VestoBot(BOT_TOKEN)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, bot.stop_event.set)
        except NotImplementedError:
            pass
    try:
        await bot.run()
    except KeyboardInterrupt:
        bot.stop_event.set()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
