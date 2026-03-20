from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import get_student_menu
from app.states import RegistrationStates
from database import create_user


router = Router()


@router.message(RegistrationStates.waiting_for_full_name)
async def process_full_name(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Пожалуйста, введите ФИО текстом.")
        return

    full_name = message.text.strip()
    if len(full_name) < 5:
        await message.answer("Пожалуйста, введите полное ФИО.")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationStates.waiting_for_class_name)
    await message.answer("Теперь введите ваш класс обучения. Например: 8А или 10.")


@router.message(RegistrationStates.waiting_for_class_name)
async def process_class_name(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Пожалуйста, введите класс текстом.")
        return

    school_class = message.text.strip()
    if len(school_class) < 1:
        await message.answer("Пожалуйста, введите корректный класс.")
        return

    data = await state.get_data()
    full_name = data["full_name"]

    await create_user(
        telegram_id=message.from_user.id,
        full_name=full_name,
        school_class=school_class,
        role="student",
    )

    await state.clear()
    await message.answer(
        "Регистрация завершена успешно.\n\n"
        f"ФИО: {full_name}\n"
        f"Класс: {school_class}",
        reply_markup=get_student_menu(),
    )

