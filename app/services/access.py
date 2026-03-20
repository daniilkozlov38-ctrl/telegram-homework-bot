from app.config import TEACHER_IDS


def is_teacher(telegram_id: int) -> bool:
    return telegram_id in TEACHER_IDS

