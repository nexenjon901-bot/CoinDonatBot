from aiogram.fsm.state import State, StatesGroup


class AddAccount(StatesGroup):
    """Eski akkaunt qo'shish (meros uchun saqlab qolindi)"""
    waiting_for_title = State()
    waiting_for_price = State()
    waiting_for_description = State()
    waiting_for_media = State()
    waiting_for_confirmation = State()


class AddCategory(StatesGroup):
    """Yangi kategoriya qo'shish"""
    waiting_for_name = State()


class AddProduct(StatesGroup):
    """Yangi mahsulot qo'shish"""
    waiting_for_category = State()
    waiting_for_name = State()
    waiting_for_price_uzs = State()
    waiting_for_price_usd = State()
    waiting_for_quantity = State()
    waiting_for_description = State()
    waiting_for_stock = State()


class BroadcastMessage(StatesGroup):
    """Barchaga xabar yuborish"""
    waiting_for_message = State()
    waiting_for_confirm = State()
