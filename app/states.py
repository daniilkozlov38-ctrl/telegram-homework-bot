from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_class_name = State()


class AssignmentStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_file = State()


class SubmissionStates(StatesGroup):
    waiting_for_solution_file = State()


class GradingStates(StatesGroup):
    waiting_for_grade = State()
    waiting_for_comment = State()
