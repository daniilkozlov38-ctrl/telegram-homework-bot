import os

from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TEACHER_IDS_RAW = os.getenv("TEACHER_IDS", "")
TEACHER_IDS = {
    int(user_id.strip())
    for user_id in TEACHER_IDS_RAW.split(",")
    if user_id.strip()
}

if not BOT_TOKEN:
    raise ValueError("Переменная BOT_TOKEN не найдена в .env")

