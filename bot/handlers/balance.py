from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Callable
import os

from bot.states.balance import BalanceFill
from core.logger import logger
from db.models.user import User
from db.models.order import BalanceRequest
from core.config import config

router = Router()

BALANCE_BANNER = "bot/images/balance_v3.png"
MIN_AMOUNT = 10_000  # Minimal to'ldirish summasi (UZS)


async def _send_balance_menu(target, text: str, keyboard):
    """Banner bilan yoki bansiz xabar yuborish"""
    banner_path = BALANCE_BANNER
    if isinstance(target, Message):
        from core.ui import answer_with_banner
        await answer_with_banner(target, banner_path, text, keyboard)
    else:  # CallbackQuery
        from core.ui import show_page
        await show_page(target, text, keyboard, banner_path)


# ───────────────────────────────────────────
# HISOBNI TO'LDIRISH — Asosiy
# ───────────────────────────────────────────

def _balance_menu_text(pe, prefix: str = "") -> str:
    from core.ui import format_uzs
    return (
        f"{pe('balance')} <b>Balansni to'ldirish</b>\n\n"
        f"{prefix}"
        f"<blockquote>Hisobingizni to'ldirish uchun qulay to'lov usulini tanlang.\n"
        f"Minimal to'lov: {format_uzs(MIN_AMOUNT)} so'm</blockquote>\n\n"
        f"<i>To'lov turini tanlang:</i>"
    )


async def show_balance_menu(message: Message, db_user: User):
    from core.emojis import create_button, pe
    builder = InlineKeyboardBuilder()
    builder.add(create_button("Karta orqali (Chek yuborish)", emoji_key="card", callback_data="balance_card_receipt"))
    builder.add(create_button("Orqaga", emoji_key="back", callback_data="balance_back"))
    builder.adjust(1)

    text = _balance_menu_text(pe)

    await _send_balance_menu(message, text, builder.as_markup())


# ───────────────────────────────────────────
# KARTA ORQALI — Chek yuborish oqimi
# ───────────────────────────────────────────

@router.callback_query(F.data == "balance_card_receipt")
async def ask_balance_amount(callback: CallbackQuery, state: FSMContext):
    from core.emojis import create_button, pe
    from core.ui import format_uzs, show_page
    builder = InlineKeyboardBuilder()
    builder.add(create_button("Bekor qilish", emoji_key="back", callback_data="balance_back"))

    text = (
        f"{pe('card')} <b>Uzcard / Humo to'lov (Chek orqali)</b>\n\n"
        f"<blockquote>Hisobingizga qancha summa o'tkazmoqchi ekanligingizni so'mda yozib yuboring.\n"
        f"Masalan: <code>10000</code> yoki <code>50000</code>\n"
        f"Minimal to'lov: {format_uzs(MIN_AMOUNT)} so'm</blockquote>"
    )

    await show_page(callback, text, builder.as_markup(), BALANCE_BANNER)

    await state.set_state(BalanceFill.waiting_for_amount)
    await callback.answer()


def _cancel_keyboard(callback_data: str):
    from core.emojis import create_button
    builder = InlineKeyboardBuilder()
    builder.add(create_button("Bekor qilish", emoji_key="back", callback_data=callback_data))
    return builder.as_markup()


@router.message(BalanceFill.waiting_for_amount, F.text)
async def process_balance_amount(message: Message, state: FSMContext, session: AsyncSession):
    text_raw = message.text.replace(" ", "").replace(",", "")
    if not text_raw.isdigit():
        from core.emojis import pe
        await message.answer(
            f"{pe('cancel')} <b>Noto'g'ri summa</b>\n\n"
            f"<blockquote>Iltimos, faqat raqam kiriting.\nMasalan: <code>50000</code></blockquote>",
            reply_markup=_cancel_keyboard("balance_back"),
        )
        return

    amount = int(text_raw)
    if amount < MIN_AMOUNT:
        from core.emojis import pe
        from core.ui import format_uzs
        await message.answer(
            f"{pe('warn')} <b>Summa juda kam</b>\n\n"
            f"<blockquote>Minimal to'ldirish summasi: <b>{format_uzs(MIN_AMOUNT)} so'm</b>\n"
            f"Iltimos, qaytadan kiriting.</blockquote>",
            reply_markup=_cancel_keyboard("balance_back"),
        )
        return

    from core.ui import format_uzs
    display_amount = f"{format_uzs(amount)} so'm"

    await state.update_data(amount=amount, display_amount=display_amount)

    # Karta ma'lumotlarini DB dan olish
    from db.models.setting import Setting, SettingKeys
    card_res = await session.execute(select(Setting).where(Setting.key == SettingKeys.PAYMENT_CARD))
    card_obj = card_res.scalar_one_or_none()
    card_number = card_obj.value if card_obj else config.PAYMENT_CARD

    owner_res = await session.execute(select(Setting).where(Setting.key == SettingKeys.PAYMENT_CARD_OWNER))
    owner_obj = owner_res.scalar_one_or_none()
    card_owner = owner_obj.value if owner_obj else config.PAYMENT_CARD_OWNER

    phone_res = await session.execute(select(Setting).where(Setting.key == SettingKeys.PAYMENT_PHONE))
    phone_obj = phone_res.scalar_one_or_none()
    phone = phone_obj.value if phone_obj else getattr(config, "PAYMENT_PHONE", "")

    from core.emojis import pe
    phone_line = f"\n{pe('phone')} Ulangan raqam: <code>{phone}</code>" if phone else ""
    text = (
        f"{pe('card')} <b>To'lov uchun rekvizitlar</b>\n\n"
        f"<blockquote>"
        f"{pe('money')} To'lov summasi: <b>{display_amount}</b>\n"
        f"{pe('card')} Karta raqami: <code>{card_number}</code>\n"
        f"{pe('profile')} Karta egasi: <b>{card_owner}</b>"
        f"{phone_line}"
        f"</blockquote>\n\n"
        f"{pe('inbox')} <b>To'lovdan keyin</b>\n"
        f"<blockquote>Ushbu botga to'lov <b>cheki (skrinshot)</b>ni yuboring. "
        f"Tekshirilib, hisobingizga mablag' qo'shiladi.</blockquote>"
    )

    await message.answer(text, reply_markup=_cancel_keyboard("balance_cancel_state"))

    await state.set_state(BalanceFill.waiting_for_receipt)


@router.message(BalanceFill.waiting_for_receipt, F.photo | F.document)
async def process_balance_receipt(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    data = await state.get_data()
    amount = data.get("amount", 0)
    display_amount = data.get("display_amount", f"{amount:,} so'm")

    file_id = message.photo[-1].file_id if message.photo else message.document.file_id

    # BalanceRequest yaratish
    req = BalanceRequest(
        user_id=db_user.id,
        amount_uzs=amount,
        receipt_file_id=file_id,
    )
    session.add(req)
    await session.commit()

    await state.clear()

    from core.emojis import pe
    text = (
        f"{pe('verify')} <b>Chekingiz qabul qilindi!</b>\n\n"
        f"<blockquote>"
        f"{pe('receipt')} So'rov: <b>#{req.id}</b>\n"
        f"{pe('money')} Miqdor: <b>{display_amount}</b>\n"
        f"{pe('pending')} Holat: <b>Tekshirilmoqda</b>"
        f"</blockquote>\n\n"
        f"Admin tekshirib, tez orada balansingizni to'ldiradi. Natija haqida shu yerda xabar olasiz."
    )
    await message.answer(text)

    # Admin ga xabar yuborish
    buyer = f"@{db_user.username}" if db_user.username else f"ID: {db_user.telegram_id}"
    admin_text = (
        f"{pe('balance')} <b>Yangi balans so'rovi</b>\n\n"
        f"<blockquote>"
        f"{pe('profile')} Foydalanuvchi: {buyer}\n"
        f"{pe('money')} Miqdor: <b>{display_amount}</b>\n"
        f"{pe('receipt')} So'rov: <b>#{req.id}</b>"
        f"</blockquote>\n\n"
        f"Tasdiqlash yoki rad etish uchun quyidagi tugmalardan foydalaning."
    )
    from aiogram import Bot
    bot: Bot = message.bot
    try:
        admin_builder = InlineKeyboardBuilder()
        admin_builder.button(text="✅ Tasdiqlash",
                             callback_data=f"bal_approve_{req.id}")
        admin_builder.button(text="❌ Rad etish",
                             callback_data=f"bal_reject_{req.id}")
        admin_builder.adjust(2)

        if file_id and message.photo:
            await bot.send_photo(
                config.ADMIN_ID,
                photo=file_id,
                caption=admin_text,
                reply_markup=admin_builder.as_markup()
            )
        else:
            await bot.send_message(config.ADMIN_ID, admin_text, reply_markup=admin_builder.as_markup())
    except Exception:
        logger.exception("Failed to send balance request notification to admin")


@router.message(BalanceFill.waiting_for_receipt)
async def waiting_receipt_hint(message: Message):
    from core.emojis import pe
    await message.answer(
        f"{pe('inbox')} <b>To'lov chekini yuboring</b>\n\n"
        f"<blockquote>Iltimos, to'lov cheki <b>rasmini (skrinshot)</b> yoki faylini yuboring.</blockquote>",
        reply_markup=_cancel_keyboard("balance_cancel_state"),
    )


@router.callback_query(F.data == "balance_back")
async def balance_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    from core.ui import show_main_menu
    await show_main_menu(callback)
    await callback.answer()


@router.callback_query(F.data == "balance_cancel_state")
async def balance_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    # Foydalanuvchini to'lov turi tanlash ekraniga qaytarish
    from core.emojis import create_button, pe
    builder = InlineKeyboardBuilder()
    builder.add(create_button("Karta orqali (Chek yuborish)", emoji_key="card", callback_data="balance_card_receipt"))
    builder.add(create_button("Orqaga", emoji_key="back", callback_data="balance_back"))
    builder.adjust(1)

    await _send_balance_menu(callback, _balance_menu_text(pe), builder.as_markup())
    await callback.answer("❌ Bekor qilindi.")
