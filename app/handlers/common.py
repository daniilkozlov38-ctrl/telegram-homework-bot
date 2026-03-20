from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import get_student_menu, get_teacher_menu
from app.services.access import is_teacher
from app.services.messages import show_main_menu
from app.states import RegistrationStates
from database import create_user, get_user_by_telegram_id


router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    telegram_id = message.from_user.id
    existing_user = await get_user_by_telegram_id(telegram_id)

    if is_teacher(telegram_id):
        if not existing_user:
            await create_user(
                telegram_id=telegram_id,
                full_name="Преподаватель",
                school_class="-",
                role="teacher",
            )

        await state.clear()
        await message.answer(
            "Вы вошли как преподаватель.\n\n"
            "Можно пользоваться кнопками ниже или командами:\n"
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

    if existing_user and not existing_user["is_active"]:
        await state.clear()
        await message.answer("Ваш аккаунт деактивирован. Обратитесь к преподавателю.")
        return

    if existing_user:
        await message.answer(
            f"Вы уже зарегистрированы.\n\n"
            f"ФИО: {existing_user['full_name']}\n"
            f"Класс: {existing_user['school_class']}\n\n"
            "Можно пользоваться кнопками ниже или командами:\n"
            "/assignments\n"
            "/grades\n"
            "/menu",
            reply_markup=get_student_menu(),
        )
        return

    await state.set_state(RegistrationStates.waiting_for_full_name)
    await message.answer(
        "Здравствуйте! Давайте зарегистрируемся.\n\n"
        "Введите ваше ФИО:"
    )


@router.message(Command("menu"))
@router.message(F.text == "Назад в меню")
async def menu_handler(message: Message, state: FSMContext) -> None:
    await show_main_menu(message, state)
