from aiogram import Bot, Dispatcher

from app.config import BOT_TOKEN
from app.handlers.common import router as common_router
from app.handlers.fallback import router as fallback_router
from app.handlers.registration import router as registration_router
from app.handlers.student import router as student_router
from app.handlers.teacher import router as teacher_router
from database import init_db


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(common_router)
    dispatcher.include_router(teacher_router)
    dispatcher.include_router(student_router)
    dispatcher.include_router(registration_router)
    dispatcher.include_router(fallback_router)
    return dispatcher


async def main() -> None:
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dispatcher = build_dispatcher()
    await dispatcher.start_polling(bot)
