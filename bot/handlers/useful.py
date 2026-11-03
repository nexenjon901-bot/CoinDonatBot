from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

USEFUL_LINKS = [
    ("📺 YouTube kanalimiz", "https://youtube.com"),
    ("💬 Telegram kanalimiz", "https://t.me/coindonat_support"),
]


async def show_useful(message: Message):
    from core.config import config
    DISCOUNTS_CHANNEL_URL = config.SUPPORT_URL

    builder = InlineKeyboardBuilder()
    for name, url in USEFUL_LINKS:
        builder.button(text=name, url=url)
    builder.button(text="📢 Kanalga o'tish", url=DISCOUNTS_CHANNEL_URL)
    builder.button(text="↩️ Orqaga", callback_data="menu_back")
    builder.adjust(1)

    text = (
        "📰 <b>Foydali ma'lumotlar</b>\n\n"
        "<blockquote>Botimiz 24/7 rejimda avtomatik ishlaydi.\n"
        "Barcha tovarlar xarid qilingan zahoti beriladi.\n"
        "Kafolat va xavfsizlik 100% ta'minlangan!</blockquote>"
    )
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "menu_back")
async def menu_back(callback: CallbackQuery):
    from bot.handlers.registration import get_main_menu_keyboard
    from core.config import config
    is_admin = callback.from_user.id == config.ADMIN_ID

    text = (
        "👋 <b>Salom!</b>\n\n"
        "<blockquote>Bu PUBG Mobile va o'yin akkauntlari do'koni boti! "
        "Kerakli bo'limni tanlang va qulay xarid qiling.</blockquote>"
    )
    keyboard = get_main_menu_keyboard(lambda x: x, is_admin=is_admin)
    try:
        await callback.message.edit_caption(caption=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()
