from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Callable
import os
import random

from bot.states.balance import BalanceFill
from core.logger import logger
from db.models.user import User
from db.models.order import BalanceRequest
from core.config import config

router = Router()

BALANCE_BANNER = "bot/images/balance.png"
MIN_AMOUNT = 10_000  # Minimal to'ldirish summasi (UZS)


async def _send_balance_menu(target, text: str, keyboard):
    """Banner bilan yoki bansiz xabar yuborish"""
    banner_path = BALANCE_BANNER
    if isinstance(target, Message):
        from core.ui import answer_with_banner
        await answer_with_banner(target, banner_path, text, keyboard)
    else:  # CallbackQuery
        try:
            await target.message.edit_caption(caption=text, reply_markup=keyboard)
        except Exception:
            await target.message.edit_text(text=text, reply_markup=keyboard)


# ───────────────────────────────────────────
# HISOBNI TO'LDIRISH — Asosiy
# ───────────────────────────────────────────

async def show_balance_menu(message: Message, db_user: User):
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Karta orqali (Chek yuborish)",
                   callback_data="balance_card_receipt")
    builder.button(text="↩️ Orqaga", callback_data="balance_back")
    builder.adjust(1)

    text = (
        f"💸 <b>Hisobni to'ldirish</b>\n\n"
        f"Hisobingizni to'ldirish uchun qulay to'lov usulini tanlang.\n"
        f"Minimal to'ldirish summasi: <b>{MIN_AMOUNT:,} so'm</b>\n\n"
        f"💳 Joriy balans: <b>{float(db_user.balance or 0):,.0f} so'm</b>\n\n"
        f"<i>To'lov turini tanlang:</i>"
    )

    await _send_balance_menu(message, text, builder.as_markup())


# ───────────────────────────────────────────
# KARTA ORQALI — Chek yuborish oqimi
# ───────────────────────────────────────────

@router.callback_query(F.data == "balance_card_receipt")
async def ask_balance_amount(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="balance_back")
    builder.adjust(1)

    text = (
        f"💸 <b>Hisobni to'ldirish</b>\n\n"
        f"💳 <b>Karta orqali (Chek yuborish)</b>\n\n"
        f"Qancha miqdorda to'ldirmoqchisiz?\n"
        f"Minimal to'ldirish summasi: <b>{MIN_AMOUNT:,} so'm</b>\n\n"
        f"Miqdorni raqamda kiriting (masalan: <code>50000</code>):"
    )

    try:
        await callback.message.edit_caption(caption=text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.edit_text(text=text, reply_markup=builder.as_markup())

    await state.set_state(BalanceFill.waiting_for_amount)
    await callback.answer()


@router.message(BalanceFill.waiting_for_amount, F.text)
async def process_balance_amount(message: Message, state: FSMContext, session: AsyncSession):
    text_raw = message.text.replace(" ", "").replace(",", "")
    if not text_raw.isdigit():
        await message.answer("❌ Iltimos, faqat raqam kiriting!\nMasalan: <code>50000</code>")
        return

    amount = int(text_raw)
    if amount < MIN_AMOUNT:
        await message.answer(f"❌ Minimal to'ldirish summasi: <b>{MIN_AMOUNT:,} so'm</b>\nBoshqa miqdor kiriting:")
        return

    # Noyob summa: asosiy summaga tasodifiy 2 xonali tiyinlar qo'shish
    random_cents = random.randint(1, 99)
    display_amount = f"{amount:,},{random_cents:02d} so'm"

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

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="balance_cancel_state")
    builder.adjust(1)

    text = (
        f"To'lov uchun rekvizitlar:\n"
        f"• To'lov summasi: {display_amount}\n"
        f"• Karta raqami: {card_number}\n"
        f"• Karta egasi: {card_owner}\n"
        f"• Ulangan raqam: {phone}\n"
        f"To'lovni amalga oshirgach, ushbu botga to'lov cheki (skrinshot)ni yuboring.\n"
        f"Tekshirilib, hisobingizga darhol mablag' qo'shiladi!"
    )

    await message.answer(text, reply_markup=builder.as_markup())

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

    text = (
        f"✅ <b>Chekingiz qabul qilindi!</b>\n\n"
        f"💰 So'ralgan miqdor: <b>{display_amount}</b>\n"
        f"⏳ Admin tekshirib, tez orada balansingizni to'ldiradi.\n\n"
        f"📦 Balans holati haqida xabar olasiz."
    )
    await message.answer(text)

    # Admin ga xabar yuborish
    buyer = f"@{db_user.username}" if db_user.username else f"ID: {db_user.telegram_id}"
    admin_text = (
        f"💰 <b>YANGI BALANS SO'ROVI</b>\n\n"
        f"👤 Foydalanuvchi: {buyer}\n"
        f"💵 Miqdor: <b>{display_amount}</b>\n"
        f"🔑 So'rov ID: #{req.id}\n\n"
        f"Tasdiqlash yoki rad etish uchun admin panelga o'ting."
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


@router.callback_query(F.data == "balance_back")
async def balance_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    from bot.handlers.registration import get_main_menu_keyboard
    from core.config import config
    is_admin = callback.from_user.id == config.ADMIN_ID

    text = (
        "👋 <b>Salom!</b>\n\n"
        "<blockquote>Bu PUBG Mobile va o'yin akkauntlari do'koni boti! "
        "Kerakli bo'limni tanlang va qulay xarid qiling.</blockquote>"
    )
    try:
        await callback.message.edit_caption(caption=text, reply_markup=get_main_menu_keyboard(lambda x: x, is_admin=is_admin))
    except Exception:
        await callback.message.edit_text(text=text, reply_markup=get_main_menu_keyboard(lambda x: x, is_admin=is_admin))
    await callback.answer()


@router.callback_query(F.data == "balance_cancel_state")
async def balance_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    # Foydalanuvchini to'lov turi tanlash ekraniga qaytarish
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Karta orqali (Chek yuborish)",
                   callback_data="balance_card_receipt")
    builder.button(text="↩️ Orqaga", callback_data="balance_back")
    builder.adjust(1)

    text = (
        f"💸 <b>Hisobni to'ldirish</b>\n\n"
        f"❌ <b>Bekor qilindi.</b>\n\n"
        f"Minimal to'ldirish summasi: <b>{MIN_AMOUNT:,} so'm</b>\n\n"
        f"<i>To'lov turini tanlang:</i>"
    )

    try:
        await callback.message.edit_caption(caption=text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.edit_text(text=text, reply_markup=builder.as_markup())

    await callback.answer("❌ Bekor qilindi.")
