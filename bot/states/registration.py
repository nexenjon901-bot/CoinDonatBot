from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    language_selection = State()
    phone_number = State()
