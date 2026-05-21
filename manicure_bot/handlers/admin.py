# handlers/admin.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime

from config import config
from states.admin import AdminStates
from keyboards.admin import admin_menu_kb
from database import (
    add_work_day,
    add_time_slot,
    delete_time_slot,
    close_day,
    get_schedule_for_date,
)

admin_router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID


@admin_router.message(F.text == "/admin")
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.set_state(AdminStates.choosing_action)
    await message.answer(
        "<b>Админ-панель</b>\nВыберите действие:",
        reply_markup=admin_menu_kb(),
    )


@admin_router.callback_query(AdminStates.choosing_action, F.data == "admin_add_day")
async def admin_add_day_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.add_day_date)
    await call.message.edit_text("Введите дату рабочего дня в формате YYYY-MM-DD:")


@admin_router.message(AdminStates.add_day_date)
async def admin_add_day_finish(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("Неверный формат даты. Используйте YYYY-MM-DD.")
        return

    add_work_day(date_str)
    await state.set_state(AdminStates.choosing_action)
    await message.answer(
        f"Рабочий день {date_str} добавлен.", reply_markup=admin_menu_kb()
    )


@admin_router.callback_query(AdminStates.choosing_action, F.data == "admin_add_slot")
async def admin_add_slot_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.add_slot_date)
    await call.message.edit_text("Введите дату для слота (YYYY-MM-DD):")


@admin_router.message(AdminStates.add_slot_date)
async def admin_add_slot_date(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("Неверный формат даты. Используйте YYYY-MM-DD.")
        return

    await state.update_data(slot_date=date_str)
    await state.set_state(AdminStates.add_slot_time)
    await message.answer("Введите время слота (HH:MM):")


@admin_router.message(AdminStates.add_slot_time)
async def admin_add_slot_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await message.answer("Неверный формат времени. Используйте HH:MM.")
        return

    data = await state.get_data()
    date_str = data.get("slot_date")
    add_time_slot(date_str, time_str)

    await state.set_state(AdminStates.choosing_action)
    await message.answer(
        f"Слот {date_str} {time_str} добавлен.", reply_markup=admin_menu_kb()
    )


@admin_router.callback_query(AdminStates.choosing_action, F.data == "admin_delete_slot")
async def admin_delete_slot_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.delete_slot_date)
    await call.message.edit_text("Введите дату слота для удаления (YYYY-MM-DD):")


@admin_router.message(AdminStates.delete_slot_date)
async def admin_delete_slot_date(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("Неверный формат даты. Используйте YYYY-MM-DD.")
        return

    await state.update_data(del_slot_date=date_str)
    await state.set_state(AdminStates.delete_slot_time)
    await message.answer("Введите время слота для удаления (HH:MM):")


@admin_router.message(AdminStates.delete_slot_time)
async def admin_delete_slot_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await message.answer("Неверный формат времени. Используйте HH:MM.")
        return

    data = await state.get_data()
    date_str = data.get("del_slot_date")
    delete_time_slot(date_str, time_str)

    await state.set_state(AdminStates.choosing_action)
    await message.answer(
        f"Слот {date_str} {time_str} удалён.", reply_markup=admin_menu_kb()
    )


@admin_router.callback_query(AdminStates.choosing_action, F.data == "admin_close_day")
async def admin_close_day_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.close_day_date)
    await call.message.edit_text("Введите дату дня, который нужно закрыть (YYYY-MM-DD):")


@admin_router.message(AdminStates.close_day_date)
async def admin_close_day_finish(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("Неверный формат даты. Используйте YYYY-MM-DD.")
        return

    close_day(date_str)
    await state.set_state(AdminStates.choosing_action)
    await message.answer(
        f"День {date_str} полностью закрыт.", reply_markup=admin_menu_kb()
    )


@admin_router.callback_query(AdminStates.choosing_action, F.data == "admin_view_schedule")
async def admin_view_schedule_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.view_schedule_date)
    await call.message.edit_text("Введите дату для просмотра расписания (YYYY-MM-DD):")


@admin_router.message(AdminStates.view_schedule_date)
async def admin_view_schedule_finish(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("Неверный формат даты. Используйте YYYY-MM-DD.")
        return

    rows = get_schedule_for_date(date_str)
    if not rows:
        await state.set_state(AdminStates.choosing_action)
        await message.answer(
            f"На дату {date_str} нет слотов.",
            reply_markup=admin_menu_kb(),
        )
        return

    lines = [f"<b>Расписание на {date_str}:</b>"]
    for r in rows:
        time_str = r["time"]
        if r["is_booked"]:
            name = r["name"] or "—"
            phone = r["phone"] or "—"
            lines.append(f"{time_str} — ЗАНЯТО ({name}, {phone})")
        else:
            lines.append(f"{time_str} — свободно")

    text = "\n".join(lines)
    await state.set_state(AdminStates.choosing_action)
    await message.answer(text, reply_markup=admin_menu_kb())