import os
from typing import Optional, Union
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InputMediaPhoto

MAIN_MENU_BANNER = "bot/images/menu.png"
SHOP_BANNER = "bot/images/shop.png"
PRODUCT_BANNER = "bot/images/product_detail.png"
PROFILE_BANNER = "bot/images/profile.png"
BALANCE_BANNER = "bot/images/balance.png"
USEFUL_BANNER = "bot/images/useful.png"

USD_RATE = 11880
MIN_BALANCE_TOPUP = 10_000

# File_id kesh — diskdan qayta-qayta yuklamaslik va bot tezligini bir necha barobar oshirish uchun
_FILE_ID_CACHE: dict[str, str] = {}


def get_cached_banner_media(path: str) -> Optional[Union[str, FSInputFile]]:
    """
    Agar file_id allaqachon keshda bo'lsa uni qaytaradi,
    aks holda FSInputFile qaytaradi.
    """
    if path in _FILE_ID_CACHE:
        return _FILE_ID_CACHE[path]
    if os.path.exists(path):
        return FSInputFile(path)
    return None


def cache_file_id(path: str, file_id: str):
    """Yangi yuborilgan rasmning file_id sini keshga saqlash"""
    if path and file_id:
        _FILE_ID_CACHE[path] = file_id


def main_menu_caption(first_name: str) -> str:
    name = first_name or "Do'st"
    return (
        f"👋 <b>Salom, {name}!</b>\n\n"
        f"<blockquote>"
        f"Bu PUBG Mobile va o'yin akkauntlari do'koni boti! "
        f"Kerakli bo'limni tanlang va qulay xarid qiling."
        f"</blockquote>"
    )


def main_menu_caption_short() -> str:
    return (
        "👋 <b>Asosiy menyu</b>\n\n"
        "🪙 <b>COIN DONAT BOT</b> — PUBG Mobile va o'yin akkauntlari do'koni boti!"
    )


async def answer_with_banner(
    message: Message,
    banner_path: str,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> Message:
    photo = get_cached_banner_media(banner_path)
    if photo:
        sent = await message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=reply_markup,
        )
        if isinstance(photo, FSInputFile) and sent.photo:
            cache_file_id(banner_path, sent.photo[-1].file_id)
        return sent
    else:
        return await message.answer(text, reply_markup=reply_markup)


def format_uzs(amount) -> str:
    return f"{float(amount):,.0f}".replace(",", " ")
