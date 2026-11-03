"""
UI Yordamchilari — Matnli, o'ta tezkor interfeys (Rasmlarsiz).
"""

from typing import Optional
from aiogram.types import Message, InlineKeyboardMarkup

USD_RATE = 11880
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
        "🪙 <b>COIN DONAT BOT</b> — PUBG Mobile va o'yin akkauntlari do'koni boti!"
    )


async def answer_with_banner(
    message: Message,
    banner_path: str = "",
    text: str = "",
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> Message:
    """Rasmsiz — toza va bir zumda javob beruvchi matnli xabar"""
    return await message.answer(text, reply_markup=reply_markup)


def format_uzs(amount) -> str:
    return f"{float(amount):,.0f}".replace(",", " ")
