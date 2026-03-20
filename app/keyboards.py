from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def get_teacher_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Список учеников"),
                KeyboardButton(text="Новое задание"),
            ],
            [
                KeyboardButton(text="Непроверенные решения"),
                KeyboardButton(text="Назад в меню"),
            ],
        ],
        resize_keyboard=True,
    )


def get_student_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Мои задания"),
                KeyboardButton(text="Назад в меню"),
            ],
        ],
        resize_keyboard=True,
    )


def get_submission_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Завершить отправку решения")],
            [KeyboardButton(text="Отмена отправки"), KeyboardButton(text="Назад в меню")],
        ],
        resize_keyboard=True,
    )


def build_students_keyboard(students) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{student['full_name']} ({student['school_class']})",
                callback_data=f"select_student:{student['id']}",
            )
        ]
        for student in students
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_assignments_keyboard(assignments_with_numbers) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"Задание #{number}: {assignment['title']}",
                callback_data=f"open_assignment:{assignment['id']}",
            )
        ]
        for assignment, number in assignments_with_numbers
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_open_assignment_keyboard(assignment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отправить решение",
                    callback_data=f"submit_assignment:{assignment_id}",
                )
            ]
        ]
    )


def build_submission_students_keyboard(submissions) -> InlineKeyboardMarkup:
    seen_students = set()
    buttons = []

    for submission in submissions:
        student_id = submission["student_id"]
        if student_id in seen_students:
            continue

        seen_students.add(student_id)
        buttons.append(
            [
                InlineKeyboardButton(
                    text=submission["student_full_name"],
                    callback_data=f"review_student:{student_id}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_submission_assignments_keyboard(student_submissions) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"Задание #{assignment_number}: {submission['assignment_title']}",
                callback_data=f"review_submission:{submission['id']}",
            )
        ]
        for submission, assignment_number in student_submissions
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
