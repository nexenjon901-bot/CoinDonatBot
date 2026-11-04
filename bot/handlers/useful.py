from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

USEFUL_BANNER = "bot/images/useful.png"


async def show_useful(message: Message):
    from core.emojis import create_button, pe
    from core.ui import answer_with_banner

    builder = InlineKeyboardBuilder()
    builder.add(create_button("Orqaga", emoji_key="back", callback_data="menu_back"))

    text = (
        f"{pe('useful')} <b>Foydali ma'lumotlar</b>\n\n"
        "<blockquote>Botimiz 24/7 rejimda avtomatik ishlaydi.\n"
        "Barcha tovarlar xarid qilingan zahoti beriladi.\n"
        "Kafolat va xavfsizlik 100% ta'minlangan!</blockquote>"
    )
    await answer_with_banner(message, USEFUL_BANNER, text, builder.as_markup())


@router.callback_query(F.data == "menu_back")
async def menu_back(callback: CallbackQuery):
    from core.ui import show_main_menu
    await show_main_menu(callback)
    await callback.answer()
