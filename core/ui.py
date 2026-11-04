"""
UI Yordamchilari — Banner (rasm) va matn bilan tez interfeys.
File ID keshlash orqali rasmlar bir marta yuklanadi, keyingi safar cache ishlatiladi.
"""

import os
from typing import Optional
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InputMediaPhoto, FSInputFile

USD_RATE = 11880
MIN_BALANCE_TOPUP = 10_000

# Banner file_id keshlari — bir marta yuklanadi, keyingi safar tez ishlaydi
_FILE_ID_CACHE: dict[str, str] = {}


def main_menu_caption(first_name: str) -> str:
    from core.emojis import pe
    name = first_name or "Do'st"
    return (
        f"{pe('wave')} <b>Salom, {name}!</b>\n\n"
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
    """
    Banner (rasm) bilan xabar yuborish.
    Birinchi yuklashda FSInputFile ishlatiladi, keyingi safarlarda file_id keshdan olinadi.
    Agar rasm topilmasa yoki yuborilmasa — oddiy matnli xabar yuboriladi.
    """
    if not banner_path:
        return await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")

    if banner_path in _FILE_ID_CACHE:
        photo = _FILE_ID_CACHE[banner_path]
    elif os.path.exists(banner_path):
        photo = FSInputFile(banner_path)
    else:
        return await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")

    try:
        sent = await message.answer_photo(
            photo=photo, caption=text, reply_markup=reply_markup, parse_mode="HTML",
        )
        if isinstance(photo, FSInputFile) and sent.photo:
            _FILE_ID_CACHE[banner_path] = sent.photo[-1].file_id
        return sent
    except Exception:
        _FILE_ID_CACHE.pop(banner_path, None)
        return await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")


async def show_page(
    callback: CallbackQuery,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    banner_path: str = "",
) -> None:
    """
    Callback xabarini yangi sahifa bilan almashtiradi.
    - banner_path berilsa va xabar rasmli bo'lsa: rasm ham, matn ham almashadi (edit_media).
    - banner_path bo'sh va xabar matnli bo'lsa: oddiy edit_text.
    - Aks holda eski xabar o'chirilib, yangisi yuboriladi.
    """
    msg = callback.message
    has_photo = bool(msg.photo)
    try:
        if banner_path and has_photo and (banner_path in _FILE_ID_CACHE or os.path.exists(banner_path)):
            media = _FILE_ID_CACHE.get(banner_path) or FSInputFile(banner_path)
            res = await msg.edit_media(
                InputMediaPhoto(media=media, caption=text, parse_mode="HTML"),
                reply_markup=reply_markup,
            )
            if isinstance(media, FSInputFile) and getattr(res, "photo", None):
                _FILE_ID_CACHE[banner_path] = res.photo[-1].file_id
            return
        if not banner_path and not has_photo:
            await msg.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
            return
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
    except Exception:
        pass

    try:
        await msg.delete()
    except Exception:
        pass
    await answer_with_banner(msg, banner_path, text, reply_markup)


async def show_main_menu(callback: CallbackQuery) -> None:
    """Asosiy menyuga qaytish (ASOSIY MENYU banneri bilan)"""
    from bot.handlers.registration import get_main_menu_keyboard, MAIN_MENU_BANNER
    from core.config import config
    is_admin = callback.from_user.id == config.ADMIN_ID
    await show_page(
        callback,
        main_menu_caption(callback.from_user.first_name),
        get_main_menu_keyboard(lambda x: x, is_admin=is_admin),
        MAIN_MENU_BANNER,
    )


def format_uzs(amount) -> str:
    return f"{float(amount):,.0f}".replace(",", " ")
