# utils/scheduler_utils.py
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from database import get_all_future_bookings

REMINDER_PREFIX = "reminder_"  # id задачи = reminder_<slot_id>


def get_job_id(slot_id: int) -> str:
    return f"{REMINDER_PREFIX}{slot_id}"


async def send_reminder(bot: Bot, user_id: int, time_str: str):
    text = (
        f"Напоминаем, что вы записаны на наращивание ресниц "
        f"завтра в {time_str}.\nЖдём вас ❤️"
    )
    await bot.send_message(chat_id=user_id, text=text)


def schedule_reminder_for_slot(
    scheduler: AsyncIOScheduler,
    bot: Bot,
    slot_id: int,
    date_str: str,
    time_str: str,
    user_tg_id: int,
):
    """Создать задачу напоминания за 24 часа до визита, если до визита >24ч."""
    visit_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    now = datetime.now()
    delta = visit_dt - now
    if delta <= timedelta(hours=24):
        return  # не создаём

    run_date = visit_dt - timedelta(hours=24)
    job_id = get_job_id(slot_id)

    scheduler.add_job(
        send_reminder,
        "date",
        run_date=run_date,
        id=job_id,
        kwargs={"bot": bot, "user_id": user_tg_id, "time_str": time_str},
        misfire_grace_time=3600,
    )


def cancel_reminder_for_slot(scheduler: AsyncIOScheduler, slot_id: int):
    job_id = get_job_id(slot_id)
    try:
        scheduler.remove_job(job_id)
    except Exception:
        # если задачи нет — просто игнорируем
        pass


def restore_all_reminders(scheduler: AsyncIOScheduler, bot: Bot):
    """Восстановление задач при старте бота."""
    bookings = get_all_future_bookings()
    for row in bookings:
        slot_id = row["id"]
        time_str = row["time"]
        date_str = row["date"]
        user_tg_id = row["tg_id"]
        schedule_reminder_for_slot(
            scheduler=scheduler,
            bot=bot,
            slot_id=slot_id,
            date_str=date_str,
            time_str=time_str,
            user_tg_id=user_tg_id,
        )