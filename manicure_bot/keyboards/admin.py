# keyboards/admin.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_menu_kb() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="➕ Добавить рабочий день", callback_data="admin_add_day"),
        ],
        [
            InlineKeyboardButton(text="➕ Добавить слот", callback_data="admin_add_slot"),
        ],
        [
            InlineKeyboardButton(text="➖ Удалить слот", callback_data="admin_delete_slot"),
        ],
        [
            InlineKeyboardButton(text="🚫 Закрыть день", callback_data="admin_close_day"),
        ],
        [
            InlineKeyboardButton(text="📋 Расписание на дату", callback_data="admin_view_schedule"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)