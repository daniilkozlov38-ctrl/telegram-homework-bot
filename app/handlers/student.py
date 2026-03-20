from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards import (
    build_assignments_keyboard,
    build_open_assignment_keyboard,
    get_student_menu,
    get_submission_menu,
)
from app.services.access import is_teacher
from app.services.files import send_file_by_type
from app.states import SubmissionStates
from database import (
    add_submission_file,
    create_submission,
    get_assignment_by_id,
    get_assignments_for_student,
    get_latest_submission_for_assignment,
    get_student_assignment_number,
    get_user_by_telegram_id,
)


router = Router()


@router.message(Command("assignments"))
@router.message(F.text == "Мои задания")
async def assignments_handler(message: Message) -> None:
    if is_teacher(message.from_user.id):
        await message.answer("Эта функция предназначена для учеников.")
        return

    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала пройдите регистрацию через /start")
        return

    assignments = await get_assignments_for_student(user["id"])
    if not assignments:
        await message.answer("У вас пока нет заданий.", reply_markup=get_student_menu())
        return

    assignments_with_numbers = []
    for assignment in assignments:
        number = await get_student_assignment_number(user["id"], assignment["id"])
        assignments_with_numbers.append((assignment, number))

    await message.answer(
        "Ваши задания:",
        reply_markup=build_assignments_keyboard(assignments_with_numbers),
    )


@router.callback_query(F.data.startswith("open_assignment:"))
async def open_assignment_handler(callback: CallbackQuery, bot: Bot) -> None:
    if is_teacher(callback.from_user.id):
        await callback.answer("Эта кнопка предназначена для ученика", show_alert=True)
        return

    assignment_id = int(callback.data.split(":")[1])
    assignment = await get_assignment_by_id(assignment_id)
    user = await get_user_by_telegram_id(callback.from_user.id)

    if not assignment or not user or assignment["student_id"] != user["id"]:
        await callback.answer("Задание не найдено", show_alert=True)
        return

    latest_submission = await get_latest_submission_for_assignment(user["id"], assignment_id)
    assignment_number = await get_student_assignment_number(user["id"], assignment_id)

    status_text = "Статус: решение еще не отправлено."
    if latest_submission:
        if latest_submission["status"] == "graded":
            status_text = (
                "Статус: проверено.\n"
                f"Оценка: {latest_submission['grade']}\n"
                f"Комментарий: {latest_submission['teacher_comment']}"
            )
        else:
            status_text = "Статус: решение отправлено, ожидает проверки."

    await callback.message.answer(
        f"Задание #{assignment_number}: {assignment['title']}\n\n{status_text}",
        reply_markup=build_open_assignment_keyboard(assignment_id),
    )
    await send_file_by_type(
        bot=bot,
        chat_id=callback.from_user.id,
        file_id=assignment["file_id"],
        file_type=assignment["file_type"],
    )
    await callback.answer()


@router.callback_query(F.data.startswith("submit_assignment:"))
async def submit_assignment_handler(callback: CallbackQuery, state: FSMContext) -> None:
    if is_teacher(callback.from_user.id):
        await callback.answer("Эта кнопка предназначена для ученика", show_alert=True)
        return

    assignment_id = int(callback.data.split(":")[1])
    assignment = await get_assignment_by_id(assignment_id)
    user = await get_user_by_telegram_id(callback.from_user.id)

    if not assignment or not user or assignment["student_id"] != user["id"]:
        await callback.answer("Задание не найдено", show_alert=True)
        return

    await state.clear()
    await state.update_data(assignment_id=assignment_id, solution_files=[])
    await state.set_state(SubmissionStates.waiting_for_solution_file)

    await callback.message.answer(
        "Отправьте одно или несколько файлов решения.\n\n"
        "Можно отправить:\n"
        "- PDF документы\n"
        "- фотографии\n\n"
        "Когда закончите, нажмите кнопку 'Завершить отправку решения'.",
        reply_markup=get_submission_menu(),
    )
    await callback.answer()


async def append_solution_file(message: Message, state: FSMContext, file_id: str, file_type: str) -> None:
    data = await state.get_data()
    solution_files = data.get("solution_files", [])
    solution_files.append({"file_id": file_id, "file_type": file_type})
    await state.update_data(solution_files=solution_files)

    await message.answer(
        f"Файл добавлен. Сейчас прикреплено файлов: {len(solution_files)}.\n"
        "Можете отправить ещё файл или нажать 'Завершить отправку решения'.",
        reply_markup=get_submission_menu(),
    )


@router.message(SubmissionStates.waiting_for_solution_file, F.document)
async def submission_document_handler(message: Message, state: FSMContext) -> None:
    if is_teacher(message.from_user.id):
        await message.answer("Эта функция доступна ученику.")
        return

    await append_solution_file(
        message=message,
        state=state,
        file_id=message.document.file_id,
        file_type="document",
    )


@router.message(SubmissionStates.waiting_for_solution_file, F.photo)
async def submission_photo_handler(message: Message, state: FSMContext) -> None:
    if is_teacher(message.from_user.id):
        await message.answer("Эта функция доступна ученику.")
        return

    await append_solution_file(
        message=message,
        state=state,
        file_id=message.photo[-1].file_id,
        file_type="photo",
    )


@router.message(SubmissionStates.waiting_for_solution_file, F.text == "Завершить отправку решения")
async def finish_submission_handler(message: Message, state: FSMContext) -> None:
    if is_teacher(message.from_user.id):
        await message.answer("Эта функция доступна ученику.")
        return

    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        await state.clear()
        await message.answer("Сначала пройдите регистрацию через /start")
        return

    data = await state.get_data()
    assignment_id = data.get("assignment_id")
    solution_files = data.get("solution_files", [])
    assignment = await get_assignment_by_id(assignment_id)

    if not assignment or assignment["student_id"] != user["id"]:
        await state.clear()
        await message.answer("Не удалось найти задание.", reply_markup=get_student_menu())
        return

    if not solution_files:
        await message.answer(
            "Вы ещё не прикрепили ни одного файла.",
            reply_markup=get_submission_menu(),
        )
        return

    first_file = solution_files[0]
    submission_id = await create_submission(
        assignment_id=assignment_id,
        student_id=user["id"],
        file_id=first_file["file_id"],
        file_type=first_file["file_type"],
    )

    for index, file_data in enumerate(solution_files, start=1):
        await add_submission_file(
            submission_id=submission_id,
            file_id=file_data["file_id"],
            file_type=file_data["file_type"],
            position=index,
        )

    await state.clear()
    await message.answer(
        f"Ваше решение сохранено. Файлов прикреплено: {len(solution_files)}.\n"
        'Преподаватель увидит их как одну работу в разделе "Непроверенные решения".',
        reply_markup=get_student_menu(),
    )


@router.message(SubmissionStates.waiting_for_solution_file, F.text == "Отмена отправки")
async def cancel_submission_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Отправка решения отменена.",
        reply_markup=get_student_menu(),
    )


@router.message(SubmissionStates.waiting_for_solution_file)
async def submission_wrong_file_handler(message: Message) -> None:
    await message.answer(
        "Пожалуйста, отправьте PDF документ, фотографию или нажмите 'Завершить отправку решения'.",
        reply_markup=get_submission_menu(),
    )

