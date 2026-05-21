# keyboards/common.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

from database import get_available_days_for_month


def main_menu_kb() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="📅 Записаться", callback_data="menu_book"),
        ],
        [
            InlineKeyboardButton(text="❌ Отменить запись", callback_data="menu_cancel"),
        ],
        [
            InlineKeyboardButton(text="💅 Прайсы", callback_data="menu_prices"),
        ],
        [
            InlineKeyboardButton(text="📸 Портфолио", callback_data="menu_portfolio"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def subscription_kb(channel_link: str) -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="🔔 Подписаться", url=channel_link),
        ],
        [
            InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscription"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def portfolio_kb(url: str) -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="Смотреть портфолио", url=url),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def calendar_kb() -> InlineKeyboardMarkup:
    """Календарь на один месяц вперёд на основе доступных дней."""
    days = get_available_days_for_month()
    if not days:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Нет доступных дат", callback_data="noop")]
            ]
        )

    buttons = []
    week = []
    for date_str in days:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        text = dt.strftime("%d.%m")
        week.append(InlineKeyboardButton(text=text, callback_data=f"day:{date_str}"))
        if len(week) == 7:
            buttons.append(week)
            week = []
    if week:
        buttons.append(week)

    buttons.append([InlineKeyboardButton(text="⬅ В меню", callback_data="to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def times_kb(slots) -> InlineKeyboardMarkup:
    """slots: list of (id, time)."""
    kb_rows = []
    row = []
    for s in slots:
        slot_id = s["id"]
        time_str = s["time"]
        row.append(
            InlineKeyboardButton(text=time_str, callback_data=f"time:{slot_id}")
        )
        if len(row) == 3:
            kb_rows.append(row)
            row = []
    if row:
        kb_rows.append(row)
    kb_rows.append([InlineKeyboardButton(text="⬅ Назад к датам", callback_data="back_to_calendar")])
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)