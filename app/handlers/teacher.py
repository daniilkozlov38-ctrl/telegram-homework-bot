from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards import (
    build_delete_confirmation_keyboard,
    build_delete_students_keyboard,
    build_restore_students_keyboard,
    build_students_keyboard,
    build_submission_assignments_keyboard,
    build_submission_students_keyboard,
    get_student_menu,
    get_teacher_menu,
)
from app.services.access import is_teacher
from app.services.files import send_file_by_type, send_submission_files
from app.services.pdf_reports import build_teacher_grades_pdf
from app.states import AssignmentStates, GradingStates
from database import (
    create_assignment,
    delete_student,
    get_all_inactive_students,
    get_all_students,
    get_all_graded_results,
    get_assignment_by_id,
    get_inactive_student_by_id,
    get_student_assignment_number,
    get_student_by_id,
    get_submission_by_id,
    get_submission_files,
    get_ungraded_submissions,
    grade_submission,
    restore_student,
)


router = Router()


@router.message(Command("students"))
@router.message(F.text == "Список учеников")
async def students_handler(message: Message) -> None:
    if not is_teacher(message.from_user.id):
        await message.answer("Эта функция доступна только преподавателю.")
        return

    students = await get_all_students()
    if not students:
        await message.answer("Пока ни один ученик не зарегистрирован.")
        return

    lines = ["Список учеников:\n"]
    for index, student in enumerate(students, start=1):
        lines.append(f"{index}. {student['full_name']} — {student['school_class']}")

    await message.answer("\n".join(lines), reply_markup=get_teacher_menu())


@router.message(Command("delete_student"))
@router.message(F.text == "Удалить ученика")
async def delete_student_menu_handler(message: Message) -> None:
    if not is_teacher(message.from_user.id):
        await message.answer("Эта функция доступна только преподавателю.")
        return

    students = await get_all_students()
    if not students:
        await message.answer("Пока ни один ученик не зарегистрирован.")
        return

    await message.answer(
        "Выберите ученика, которого нужно удалить:",
        reply_markup=build_delete_students_keyboard(students),
    )


@router.message(Command("new_assignment"))
@router.message(F.text == "Новое задание")
async def new_assignment_handler(message: Message, state: FSMContext) -> None:
    if not is_teacher(message.from_user.id):
        await message.answer("Эта функция доступна только преподавателю.")
        return

    students = await get_all_students()
    if not students:
        await message.answer("Сначала дождитесь регистрации хотя бы одного ученика.")
        return

    await state.clear()
    await message.answer(
        "Выберите ученика, которому хотите выдать задание:",
        reply_markup=build_students_keyboard(students),
    )


@router.message(Command("restore_student"))
@router.message(F.text == "Восстановить ученика")
async def restore_student_menu_handler(message: Message) -> None:
    if not is_teacher(message.from_user.id):
        await message.answer("Эта функция доступна только преподавателю.")
        return

    students = await get_all_inactive_students()
    if not students:
        await message.answer("Нет деактивированных учеников.", reply_markup=get_teacher_menu())
        return

    await message.answer(
        "Выберите ученика, которого нужно восстановить:",
        reply_markup=build_restore_students_keyboard(students),
    )


@router.callback_query(F.data.startswith("select_student:"))
async def select_student_handler(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_teacher(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    student_id = int(callback.data.split(":")[1])
    student = await get_student_by_id(student_id)
    if not student:
        await callback.answer("Ученик не найден", show_alert=True)
        return

    await state.update_data(student_id=student_id)
    await state.set_state(AssignmentStates.waiting_for_title)
    await callback.message.answer(
        f"Вы выбрали ученика: {student['full_name']}\n\n"
        "Теперь введите название задания."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_student:"))
async def delete_student_handler(callback: CallbackQuery) -> None:
    if not is_teacher(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    student_id = int(callback.data.split(":")[1])
    student = await get_student_by_id(student_id)
    if not student:
        await callback.answer("Ученик не найден", show_alert=True)
        return

    await callback.message.answer(
        f"Удалить ученика {student['full_name']} ({student['school_class']})?\n"
        "Ученик будет деактивирован и исчезнет из активных списков, но его данные останутся в базе.",
        reply_markup=build_delete_confirmation_keyboard(student_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_student:"))
async def confirm_delete_student_handler(callback: CallbackQuery) -> None:
    if not is_teacher(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    student_id = int(callback.data.split(":")[1])
    student = await get_student_by_id(student_id)
    if not student:
        await callback.answer("Ученик уже удалён", show_alert=True)
        return

    student_name = student["full_name"]
    await delete_student(student_id)
    await callback.message.answer(
        f"Ученик {student_name} деактивирован.",
        reply_markup=get_teacher_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_delete_student")
async def cancel_delete_student_handler(callback: CallbackQuery) -> None:
    if not is_teacher(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    await callback.message.answer(
        "Удаление ученика отменено.",
        reply_markup=get_teacher_menu(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("restore_student:"))
async def restore_student_handler(callback: CallbackQuery) -> None:
    if not is_teacher(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    student_id = int(callback.data.split(":")[1])
    student = await get_inactive_student_by_id(student_id)
    if not student:
        await callback.answer("Ученик не найден или уже восстановлен", show_alert=True)
        return

    await restore_student(student_id)
    await callback.message.answer(
        f"Ученик {student['full_name']} восстановлен.",
        reply_markup=get_teacher_menu(),
    )
    await callback.answer()


@router.message(AssignmentStates.waiting_for_title)
async def assignment_title_handler(message: Message, state: FSMContext) -> None:
    if not is_teacher(message.from_user.id):
        await message.answer("Эта функция доступна только преподавателю.")
        return

    if not message.text:
        await message.answer("Введите название задания текстом.")
        return

    title = message.text.strip()
    if len(title) < 2:
        await message.answer("Название задания слишком короткое. Введите нормальное название.")
        return

    await state.update_data(title=title)
    await state.set_state(AssignmentStates.waiting_for_file)
    await message.answer(
        "Теперь отправьте файл задания.\n\n"
        "Можно отправить:\n"
        "- PDF документ\n"
        "- фотографию"
    )


async def save_assignment_and_notify(
    message: Message,
    state: FSMContext,
    bot: Bot,
    file_id: str,
    file_type: str,
) -> None:
    data = await state.get_data()
    student_id = data["student_id"]
    title = data["title"]

    await create_assignment(
        student_id=student_id,
        title=title,
        file_id=file_id,
        file_type=file_type,
    )

    student = await get_student_by_id(student_id)
    await bot.send_message(
        chat_id=student["telegram_id"],
        text=f"Вам добавили новое задание: {title}",
        reply_markup=get_student_menu(),
    )
    await send_file_by_type(
        bot=bot,
        chat_id=student["telegram_id"],
        file_id=file_id,
        file_type=file_type,
        caption=f"Новое задание: {title}",
    )

    await state.clear()
    await message.answer(
        "Задание успешно создано и отправлено ученику.",
        reply_markup=get_teacher_menu(),
    )


@router.message(AssignmentStates.waiting_for_file, F.document)
async def assignment_document_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    if not is_teacher(message.from_user.id):
        await message.answer("Эта функция доступна только преподавателю.")
        return

    await save_assignment_and_notify(
        message=message,
        state=state,
        bot=bot,
        file_id=message.document.file_id,
        file_type="document",
    )


@router.message(AssignmentStates.waiting_for_file, F.photo)
async def assignment_photo_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    if not is_teacher(message.from_user.id):
        await message.answer("Эта функция доступна только преподавателю.")
        return

    await save_assignment_and_notify(
        message=message,
        state=state,
        bot=bot,
        file_id=message.photo[-1].file_id,
        file_type="photo",
    )


@router.message(AssignmentStates.waiting_for_file)
async def assignment_wrong_file_handler(message: Message) -> None:
    await message.answer("Пожалуйста, отправьте PDF документ или фотографию.")


@router.message(Command("submissions"))
@router.message(F.text == "Непроверенные решения")
async def submissions_handler(message: Message) -> None:
    if not is_teacher(message.from_user.id):
        await message.answer("Эта функция доступна только преподавателю.")
        return

    submissions = await get_ungraded_submissions()
    if not submissions:
        await message.answer("Непроверенных решений пока нет.", reply_markup=get_teacher_menu())
        return

    await message.answer(
        "Выберите ученика:",
        reply_markup=build_submission_students_keyboard(submissions),
    )


@router.message(Command("grades_report"))
@router.message(F.text == "Таблица оценок")
async def grades_report_handler(message: Message) -> None:
    if not is_teacher(message.from_user.id):
        await message.answer("Эта функция доступна только преподавателю.")
        return

    graded_results = await get_all_graded_results()
    if not graded_results:
        await message.answer(
            "Пока нет проверенных работ с оценками.",
            reply_markup=get_teacher_menu(),
        )
        return

    student_results: dict[str, list[tuple[str, str]]] = {}
    for result in graded_results:
        student_label = f"{result['student_full_name']} ({result['school_class']})"
        assignment_label = f"{result['assignment_number']} ({result['assignment_title']})"

        if student_label not in student_results:
            student_results[student_label] = []

        student_results[student_label].append(
            (
                assignment_label,
                str(result["grade"]),
            )
        )

    student_labels = list(student_results.keys())
    max_assignments = max(len(items) for items in student_results.values())

    rows = [["", *student_labels]]
    for index in range(max_assignments):
        assignment_row = [f"ДЗ {index + 1}"]
        grade_row = [f"Оценка {index + 1}"]

        for student_label in student_labels:
            student_items = student_results[student_label]
            if index < len(student_items):
                assignment_label, grade = student_items[index]
                assignment_row.append(assignment_label)
                grade_row.append(grade)
            else:
                assignment_row.append("")
                grade_row.append("")

        rows.append(assignment_row)
        rows.append(grade_row)

    pdf_file = build_teacher_grades_pdf(rows)
    await message.answer_document(
        pdf_file,
        caption="Вот общая таблица оценок в PDF.",
        reply_markup=get_teacher_menu(),
    )


@router.callback_query(F.data.startswith("review_student:"))
async def review_student_handler(callback: CallbackQuery) -> None:
    if not is_teacher(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    student_id = int(callback.data.split(":")[1])
    submissions = await get_ungraded_submissions()
    student_submissions = []

    for submission in submissions:
        if submission["student_id"] != student_id:
            continue

        assignment_number = await get_student_assignment_number(
            student_id,
            submission["assignment_id"],
        )
        student_submissions.append((submission, assignment_number))

    if not student_submissions:
        await callback.answer("У этого ученика нет непроверенных решений", show_alert=True)
        return

    await callback.message.answer(
        "Выберите задание:",
        reply_markup=build_submission_assignments_keyboard(student_submissions),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("review_submission:"))
async def review_submission_handler(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not is_teacher(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    submission_id = int(callback.data.split(":")[1])
    submission = await get_submission_by_id(submission_id)
    if not submission:
        await callback.answer("Работа не найдена", show_alert=True)
        return

    assignment = await get_assignment_by_id(submission["assignment_id"])
    student = await get_student_by_id(submission["student_id"])
    assignment_number = await get_student_assignment_number(student["id"], assignment["id"])

    await state.clear()
    await state.update_data(submission_id=submission_id)
    await state.set_state(GradingStates.waiting_for_grade)

    await callback.message.answer(
        f"Проверка работы ученика {student['full_name']}.\n"
        f"Задание #{assignment_number}: {assignment['title']}\n\n"
        "Введите оценку."
    )

    submission_files = await get_submission_files(submission_id)
    if submission_files:
        await callback.message.answer(f"Файлов в решении: {len(submission_files)}")

    await send_submission_files(
        bot=bot,
        chat_id=callback.from_user.id,
        submission=submission,
        submission_files=submission_files,
    )
    await callback.answer()


@router.message(GradingStates.waiting_for_grade)
async def grading_grade_handler(message: Message, state: FSMContext) -> None:
    if not is_teacher(message.from_user.id):
        await message.answer("Эта функция доступна только преподавателю.")
        return

    if not message.text:
        await message.answer("Введите оценку текстом.")
        return

    grade = message.text.strip()
    if len(grade) < 1:
        await message.answer("Введите корректную оценку.")
        return

    await state.update_data(grade=grade)
    await state.set_state(GradingStates.waiting_for_comment)
    await message.answer("Теперь введите комментарий к работе.")


@router.message(GradingStates.waiting_for_comment)
async def grading_comment_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    if not is_teacher(message.from_user.id):
        await message.answer("Эта функция доступна только преподавателю.")
        return

    if not message.text:
        await message.answer("Введите комментарий текстом.")
        return

    comment = message.text.strip()
    if len(comment) < 1:
        await message.answer("Комментарий не должен быть пустым.")
        return

    data = await state.get_data()
    submission_id = data["submission_id"]
    grade = data["grade"]

    submission = await get_submission_by_id(submission_id)
    if not submission:
        await state.clear()
        await message.answer("Работа не найдена.")
        return

    assignment = await get_assignment_by_id(submission["assignment_id"])
    student = await get_student_by_id(submission["student_id"])
    assignment_number = await get_student_assignment_number(student["id"], assignment["id"])

    await grade_submission(
        submission_id=submission_id,
        grade=grade,
        teacher_comment=comment,
    )

    await bot.send_message(
        chat_id=student["telegram_id"],
        text=(
            f"Ваша работа проверена.\n\n"
            f"Задание #{assignment_number}: {assignment['title']}\n"
            f"Оценка: {grade}\n"
            f"Комментарий: {comment}"
        ),
        reply_markup=get_student_menu(),
    )

    await state.clear()
    await message.answer(
        "Оценка и комментарий отправлены ученику.",
        reply_markup=get_teacher_menu(),
    )
