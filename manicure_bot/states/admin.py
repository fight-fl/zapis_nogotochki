# states/admin.py
from aiogram.fsm.state import StatesGroup, State


class AdminStates(StatesGroup):
    choosing_action = State()
    add_day_date = State()
    add_slot_date = State()
    add_slot_time = State()
    delete_slot_date = State()
    delete_slot_time = State()
    close_day_date = State()
    view_schedule_date = State()
    cancel_booking_user_id = State()