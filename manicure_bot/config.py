# config.py
from dataclasses import dataclass

@dataclass
class Config:
    BOT_TOKEN: str = "8528196754:AAH7tvTdJdV6ZevDB6JnPBq4LCegluAPcsQ"
    ADMIN_ID: int = 702961463  # ID администратора
    CHANNEL_ID: int = -1003521081856  # ID канала (со знаком -100...)
    CHANNEL_LINK: str = "https://t.me/podpiska_test_bot_nogotochki"  # ссылка-приглашение в канал

config = Config()