# handlers/user.py
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime

from config import config
from database import (
    get_free_slots_for_date,
    book_slot,
    get_or_create_user,
    user_has_active_booking,
    cancel_booking_for_user,
    get_user_active_booking,
    get_booking_by_slot_id,
)
from keyboards.common import (
    main_menu_kb,
    calendar_kb,
    times_kb,
    subscription_kb,
    portfolio_kb,
)
from states.booking import BookingStates
from utils.scheduler_utils import schedule_reminder_for_slot, cancel_reminder_for_slot

user_router = Router()


async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=config.CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "creator", "administrator")
    except Exception:
        return False


@user_router.message(F.text == "/start")
async def cmd_start(message: Message):
    text = (
        "<b>Добро пожаловать!</b>\n\n"
        "Я бот для записи к мастеру по маникюру.\n"
        "Выберите нужный пункт в меню ниже."
    )
    await message.answer(text, reply_markup=main_menu_kb())


# ---------- Главное меню (без FSM для Прайсов и Портфолио) ----------

@user_router.callback_query(F.data == "to_menu")
async def back_to_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "Главное меню:", reply_markup=main_menu_kb()
    )


@user_router.callback_query(F.data == "menu_prices")
async def show_prices(call: CallbackQuery):
    text = (
        "<b>Прайс на услуги:</b>\n\n"
        "Френч — <b>1000₽</b>\n"
        "Квадрат — <b>500₽</b>\n"
    )
    await call.message.edit_text(text, reply_markup=main_menu_kb())


@user_router.callback_query(F.data == "menu_portfolio")
async def show_portfolio(call: CallbackQuery):
    kb = portfolio_kb("https://ru.pinterest.com/crystalwithluv/_created/")
    await call.message.edit_text("📸 Моё портфолио:", reply_markup=kb)


# ---------- Проверка подписки и старт записи ----------

@user_router.callback_query(F.data == "menu_book")
async def start_booking(call: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = call.from_user.id
    is_subscribed = await check_subscription(bot, user_id)
    if not is_subscribed:
        text = (
            "Для записи необходимо подписаться на канал.\n\n"
            "После подписки нажмите «Проверить подписку»."
        )
        await call.message.edit_text(
            text,
            reply_markup=subscription_kb(config.CHANNEL_LINK),
        )
        return

    # Проверка на уже существующую запись
    if user_has_active_booking(user_id):
        booking = get_user_active_booking(user_id)
        date_str = datetime.strptime(booking["date"], "%Y-%m-%d").strftime("%d.%m.%Y")
        time_str = booking["time"]
        await call.message.edit_text(
            f"У вас уже есть запись на <b>{date_str}</b> в <b>{time_str}</b>.\n"
            "Сначала отмените её, если хотите записаться на другое время.",
            reply_markup=main_menu_kb(),
        )
        return

    await state.set_state(BookingStates.choosing_date)
    await call.message.edit_text(
        "Выберите дату для записи:",
        reply_markup=calendar_kb(),
    )


@user_router.callback_query(F.data == "check_subscription")
async def check_subscription_button(call: CallbackQuery, bot: Bot, state: FSMContext):
    user_id = call.from_user.id
    is_subscribed = await check_subscription(bot, user_id)
    if not is_subscribed:
        await call.answer("Подписка не найдена, попробуйте ещё раз.", show_alert=True)
        return

    await state.set_state(BookingStates.choosing_date)
    await call.message.edit_text(
        "Спасибо за подписку! Теперь вы можете записаться.\n\n"
        "Выберите дату:",
        reply_markup=calendar_kb(),
    )


# ---------- FSM: выбор даты и времени ----------

@user_router.callback_query(BookingStates.choosing_date, F.data.startswith("day:"))
async def choose_date(call: CallbackQuery, state: FSMContext):
    date_str = call.data.split(":", 1)[1]
    slots = get_free_slots_for_date(date_str)
    if not slots:
        await call.answer("На эту дату нет свободных слотов.", show_alert=True)
        return

    await state.update_data(chosen_date=date_str)
    await state.set_state(BookingStates.choosing_time)
    human_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    await call.message.edit_text(
        f"Вы выбрали дату <b>{human_date}</b>.\nВыберите время:",
        reply_markup=times_kb(slots),
    )


@user_router.callback_query(BookingStates.choosing_time, F.data == "back_to_calendar")
async def back_to_calendar(call: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.choosing_date)
    await call.message.edit_text(
        "Выберите дату:",
        reply_markup=calendar_kb(),
    )


@user_router.callback_query(BookingStates.choosing_time, F.data.startswith("time:"))
async def choose_time(call: CallbackQuery, state: FSMContext):
    slot_id = int(call.data.split(":", 1)[1])
    await state.update_data(slot_id=slot_id)
    await state.set_state(BookingStates.entering_name)
    await call.message.edit_text("Введите, пожалуйста, ваше имя:")


@user_router.message(BookingStates.entering_name)
async def input_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(BookingStates.entering_phone)
    await message.answer("Введите, пожалуйста, ваш номер телефона:")


@user_router.message(BookingStates.entering_phone)
async def input_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)

    data = await state.get_data()
    date_str = data.get("chosen_date")
    slot_info = get_booking_by_slot_id(data.get("slot_id"))
    if not slot_info:
        await message.answer("Выбранный слот больше недоступен. Попробуйте снова.")
        await state.clear()
        await message.answer("Главное меню:", reply_markup=main_menu_kb())
        return

    time_str = slot_info["time"]
    human_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    name = data.get("name")

    text = (
        "<b>Проверьте данные записи:</b>\n\n"
        f"Дата: <b>{human_date}</b>\n"
        f"Время: <b>{time_str}</b>\n"
        f"Имя: <b>{name}</b>\n"
        f"Телефон: <b>{phone}</b>\n\n"
        "Подтвердить запись?"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_booking"),
            ],
            [
                InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking_flow"),
            ],
        ]
    )

    await state.set_state(BookingStates.confirming)
    await message.answer(text, reply_markup=kb)


@user_router.callback_query(BookingStates.confirming, F.data == "cancel_booking_flow")
async def cancel_booking_flow(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "Запись отменена.\nВы в главном меню.", reply_markup=main_menu_kb()
    )


@user_router.callback_query(BookingStates.confirming, F.data == "confirm_booking")
async def confirm_booking(
    call: CallbackQuery, state: FSMContext, bot: Bot
):
    data = await state.get_data()
    slot_id = data.get("slot_id")
    date_str = data.get("chosen_date")
    name = data.get("name")
    phone = data.get("phone")
    from_id = call.from_user.id

    # Проверка что у пользователя нет другой записи (повторная подстраховка)
    if user_has_active_booking(from_id):
        await state.clear()
        await call.message.edit_text(
            "У вас уже есть активная запись. Сначала отмените её.",
            reply_markup=main_menu_kb(),
        )
        return

    user_id = get_or_create_user(from_id, name=name, phone=phone)
    booked = book_slot(slot_id, user_id)
    if not booked:
        await state.clear()
        await call.message.edit_text(
            "К сожалению, выбранный слот уже занят. Попробуйте ещё раз.",
            reply_markup=main_menu_kb(),
        )
        return

    date_str, time_str = booked
    human_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")

    # Напоминание за 24 часа
    schedule_reminder_for_slot(
        scheduler=call.bot["apscheduler"],
        bot=bot,
        slot_id=slot_id,
        date_str=date_str,
        time_str=time_str,
        user_tg_id=from_id,
    )

    # Сообщение пользователю
    await state.clear()
    await call.message.edit_text(
        f"Ваша запись подтверждена!\n\n"
        f"Дата: <b>{human_date}</b>\n"
        f"Время: <b>{time_str}</b>\n"
        f"Имя: <b>{name}</b>\n"
        f"Телефон: <b>{phone}</b>\n",
        reply_markup=main_menu_kb(),
    )

    # Сообщение администратору
    admin_text = (
        "<b>Новая запись:</b>\n\n"
        f"Дата: <b>{human_date}</b>\n"
        f"Время: <b>{time_str}</b>\n"
        f"Имя: <b>{name}</b>\n"
        f"Телефон: <b>{phone}</b>\n"
        f"Telegram ID: <code>{from_id}</code>"
    )
    try:
        await bot.send_message(chat_id=config.ADMIN_ID, text=admin_text)
    except Exception:
        pass

    # Сообщение в канал с расписанием
    channel_text = (
        "<b>Новая запись в расписании:</b>\n\n"
        f"{human_date} в {time_str}\n"
        f"Клиент: <b>{name}</b>\n"
    )
    try:
        await bot.send_message(chat_id=config.CHANNEL_ID, text=channel_text)
    except Exception:
        pass


# ---------- Отмена записи пользователем ----------

@user_router.callback_query(F.data == "menu_cancel")
async def user_cancel_booking(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    booking = get_user_active_booking(user_id)
    if not booking:
        await call.message.edit_text(
            "У вас нет активных записей.", reply_markup=main_menu_kb()
        )
        return

    slot_id = booking["id"]
    date_str = booking["date"]
    time_str = booking["time"]

    # Сначала отменяем запись в базе
    result = cancel_booking_for_user(user_id)
    if not result:
        await call.message.edit_text(
            "Не удалось найти активную запись.", reply_markup=main_menu_kb()
        )
        return

    # Отмена напоминания
    cancel_reminder_for_slot(call.bot["apscheduler"], slot_id)

    human_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    await call.message.edit_text(
        f"Ваша запись на <b>{human_date}</b> в <b>{time_str}</b> отменена.",
        reply_markup=main_menu_kb(),
    )

    # Сообщение админу
    try:
        await bot.send_message(
            chat_id=config.ADMIN_ID,
            text=(
                "<b>Отмена записи:</b>\n\n"
                f"Дата: <b>{human_date}</b>\n"
                f"Время: <b>{time_str}</b>\n"
                f"Telegram ID: <code>{user_id}</code>"
            ),
        )
    except Exception:
        pass