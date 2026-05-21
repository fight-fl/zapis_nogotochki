# bot.py

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import config
from database import init_db
from handlers.user import user_router
from handlers.admin import admin_router
from utils.scheduler_utils import restore_all_reminders


async def main():
    init_db()

    bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Планировщик
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.start()

    # Сохраняем планировщик в объекте бота для доступа в хэндлерах
    bot.scheduler = scheduler

    # Восстановление напоминаний при старте
    restore_all_reminders(scheduler, bot)

    # Роутеры
    dp.include_router(user_router)
    dp.include_router(admin_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())