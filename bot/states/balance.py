from aiogram.fsm.state import State, StatesGroup


class BalanceFill(StatesGroup):
    waiting_for_amount = State()     # Miqdor kiritish
    waiting_for_receipt = State()    # Chek rasmi kutish
