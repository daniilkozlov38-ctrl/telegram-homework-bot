from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import get_student_menu, get_teacher_menu
from app.services.access import is_teacher
from database import get_user_by_telegram_id


async def show_main_menu(message: Message, state: FSMContext) -> None:
    await state.clear()

    if is_teacher(message.from_user.id):
        await message.answer(
            "Главное меню преподавателя.",
            reply_markup=get_teacher_menu(),
        )
        return

    user = await get_user_by_telegram_id(message.from_user.id)
    if user:
        await message.answer(
            "Главное меню ученика.",
            reply_markup=get_student_menu(),
        )
    else:
        await message.answer("Сначала пройдите регистрацию через /start")

