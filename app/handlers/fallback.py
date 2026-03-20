from aiogram import F, Router
from aiogram.types import Message

from app.keyboards import get_student_menu, get_teacher_menu
from app.services.access import is_teacher


router = Router()


@router.message(F.text)
async def fallback_handler(message: Message) -> None:
    if is_teacher(message.from_user.id):
        await message.answer(
            "Команда не распознана.\n\n"
            "Используйте кнопки ниже или команды:\n"
            "/students\n"
            "/new_assignment\n"
            "/submissions\n"
            "/grades_report\n"
            "/delete_student\n"
            "/restore_student\n"
            "/menu",
            reply_markup=get_teacher_menu(),
        )
        return

    await message.answer(
        "Команда не распознана.\n\n"
        "Используйте кнопки ниже или команды:\n"
        "/assignments\n"
        "/grades\n"
        "/menu",
        reply_markup=get_student_menu(),
    )
