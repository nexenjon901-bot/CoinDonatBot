from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

USEFUL_LINKS = [
    ("📺 YouTube kanalimiz", "https://youtube.com"),
    ("💬 Telegram kanalimiz", "https://t.me/entelli_sale"),
]


async def show_useful(message: Message):
    builder = InlineKeyboardBuilder()
    for name, url in USEFUL_LINKS:
        builder.button(text=name, url=url)
    builder.button(text="↩️ Orqaga", callback_data="menu_back")
    builder.adjust(1)

    text = (
        "📋 <b>Foydali havolalar</b>\n\n"
        "Quyidagi havolalar orqali biz bilan bog'laning va eng so'nggi yangiliklar bilan tanishingiz mumkin!:"
    )
    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "menu_back")
async def menu_back(callback: CallbackQuery):
    from bot.handlers.registration import get_main_menu_keyboard
    from core.config import config
    is_admin = callback.from_user.id == config.ADMIN_ID

    text = (
        "👋 <b>Asosiy menyu</b>\n\n"
        "🛍 <b>ENTELLI STORE</b> — PUBG MOBILE UC VA AKKAUNT SOTUVCHI BOTI!"
    )
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard(lambda x: x, is_admin=is_admin))
    await callback.answer()
