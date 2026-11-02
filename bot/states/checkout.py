from aiogram.fsm.state import State, StatesGroup


class Checkout(StatesGroup):
    payment_method = State()
    receipt_upload = State()


class UCCheckout(StatesGroup):
    waiting_for_player_id = State()
