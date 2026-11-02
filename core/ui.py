import os
from typing import Optional

from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup

MAIN_MENU_BANNER = "bot/images/menu.png"
SHOP_BANNER = "bot/images/shop.png"
PRODUCT_BANNER = "bot/images/product_detail.png"
PROFILE_BANNER = "bot/images/profile.png"
BALANCE_BANNER = "bot/images/balance.png"
USEFUL_BANNER = "bot/images/useful.png"

USD_RATE = 12700
MIN_BALANCE_TOPUP = 10_000


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
        "🛍 <b>ENTELLI STORE</b> — PUBG Mobile va o'yin akkauntlari do'koni boti!"
    )


async def answer_with_banner(
    message: Message,
    banner_path: str,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
):
    if os.path.exists(banner_path):
        await message.answer_photo(
            photo=FSInputFile(banner_path),
            caption=text,
            reply_markup=reply_markup,
        )
    else:
        await message.answer(text, reply_markup=reply_markup)


def format_uzs(amount) -> str:
    return f"{float(amount):,.0f}".replace(",", " ")
