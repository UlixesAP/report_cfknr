import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден! "
        "Создайте файл .env и добавьте туда BOT_TOKEN=ваш_токен"
    )

MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID")