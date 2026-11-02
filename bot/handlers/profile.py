from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from typing import Callable
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

from db.models.user import User
from db.models.order import Order, OrderStatus

router = Router()

PROFILE_BANNER = "bot/images/profile.png"


async def _build_profile_text(db_user: User, session: AsyncSession) -> str:
    """Profil ma'lumotlarini matn sifatida yaratish — storechookie_bot uslubi"""
    now = datetime.now(timezone.utc)

    # Xaridlar statistikasi
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)

    # 24 soat
    r24 = await session.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.price), 0))
        .where(Order.user_id == db_user.id, Order.status == OrderStatus.COMPLETED, Order.created_at >= day_ago)
    )
    cnt24, sum24 = r24.one()

    # 7 kun
    r7 = await session.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.price), 0))
        .where(Order.user_id == db_user.id, Order.status == OrderStatus.COMPLETED, Order.created_at >= week_ago)
    )
    cnt7, sum7 = r7.one()

    # Barcha vaqt
    rall = await session.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.price), 0))
        .where(Order.user_id == db_user.id, Order.status == OrderStatus.COMPLETED)
    )
    cntall, sumall = rall.one()

    balance = float(db_user.balance or 0)
    total_spent = float(db_user.total_spent or 0)
    username = f"@{db_user.username}" if db_user.username else "—"
    joined = db_user.created_at.strftime(
        "%b %d, %Y") if db_user.created_at else "—"

    # USD kurs (taxminiy, sozlash mumkin)
    USD_RATE = 12700
    balance_usd = balance / USD_RATE
    spent_usd = total_spent / USD_RATE

    text = (
        f"👤 <b>Sizning profilingiz</b>\n\n"
        f"• ID: <code>{db_user.telegram_id}</code>\n"
        f"• Username: {username}\n"
        f"• Ro'yxatdan o'tgan: {joined}\n"
        f"• Balans: <b>${balance_usd:.2f} ({balance:,.0f} so'm)</b>\n"
        f"• Jami sarflangan: <b>${spent_usd:.2f} ({total_spent:,.0f} so'm)</b>\n\n"
        f"Xaridlar:\n"
        f"• 24 soat: {cnt24} dona / ${float(sum24)/USD_RATE:.2f}\n"
        f"• 7 kun: {cnt7} dona / ${float(sum7)/USD_RATE:.2f}\n"
        f"• Barcha vaqt: {cntall} dona / ${float(sumall)/USD_RATE:.2f}"
    )
    return text


def _get_profile_keyboard() -> object:
    """Profil sahifasi uchun inline klaviatura — storechookie_bot uslubi"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Buyurtmalar tarixi", callback_data="profile_orders")
    builder.button(text="🎁 Chegirmalar",
                   callback_data="profile_discounts")
    builder.button(text="🌐 Bot tili",
                   callback_data="profile_change_lang")
    builder.button(text="↩️ Orqaga",             callback_data="profile_back")
    builder.adjust(1, 2, 1)
    return builder.as_markup()


# ───────────────────────────────────────────
# PROFIL — Ko'rsatish
# ───────────────────────────────────────────

async def show_profile(message: Message, session: AsyncSession, db_user: User):
    if not db_user:
        await message.answer("❌ Avval ro'yxatdan o'ting: /start")
        return

    text = await _build_profile_text(db_user, session)
    keyboard = _get_profile_keyboard()

    if os.path.exists(PROFILE_BANNER):
        await message.answer_photo(
            photo=FSInputFile(PROFILE_BANNER),
            caption=text,
            reply_markup=keyboard
        )
    else:
        await message.answer(text, reply_markup=keyboard)


# ───────────────────────────────────────────
# PROFIL — Inline tugmalar
# ───────────────────────────────────────────

@router.callback_query(F.data == "profile_orders")
async def show_orders_history(callback: CallbackQuery, session: AsyncSession, db_user: User):
    result = await session.execute(
        select(Order)
        .where(Order.user_id == db_user.id)
        .order_by(Order.created_at.desc())
        .limit(10)
    )
    orders = result.scalars().all()

    builder = InlineKeyboardBuilder()

    if not orders:
        text = "📋 <b>Buyurtmalar tarixi</b>\n\nSiz hali hech narsa sotib olmadingiz."
    else:
        lines = ["📋 <b>Buyurtmalar tarixi</b>\n\nMa'lumotlarni ko'rish uchun quyidagi tugmalardan birini tanlang:\n"]
        for o in orders:
            date = o.created_at.strftime("%d.%m.%Y") if o.created_at else "—"
            status_icons = {
                "COMPLETED": "✅", "CANCELLED": "❌", "REJECTED": "❌",
                "PAYMENT_REVIEW": "⏳", "APPROVED": "✔️", "PENDING_PAYMENT": "⏳",
                "DELIVERY_FAILED": "⚠️"
            }
            icon = status_icons.get(o.status.value if o.status else "", "❓")
            lines.append(f"{icon} <code>{o.order_number}</code> — {float(o.price):,.0f} so'm — {date}")
            
            # Add button for this order
            builder.button(text=f"{icon} {o.order_number}", callback_data=f"order_view_{o.id}")
            
        text = "\n".join(lines)

    # Adjust buttons 2 per row
    builder.adjust(2)
    # Add back button on its own row
    builder.row(InlineKeyboardBuilder().button(text="↩️ Orqaga", callback_data="profile_back_detail").as_markup().inline_keyboard[0])

    try:
        await callback.message.edit_caption(caption=text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.edit_text(text=text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("order_view_"))
async def view_order_details(callback: CallbackQuery, session: AsyncSession, db_user: User):
    order_id = int(callback.data.split("_")[2])
    
    # Check order belongs to user
    order = await session.get(Order, order_id)
    if not order or order.user_id != db_user.id:
        await callback.answer("Buyurtma topilmadi!", show_alert=True)
        return
        
    from sqlalchemy import text
    from core.security import decrypt_text
    from core.utils import format_money
    
    res = await session.execute(
        text("SELECT data_encrypted FROM stock_items WHERE order_id = :oid"),
        {"oid": order_id}
    )
    row = res.fetchone()
    
    if not row:
        await callback.answer("Ma'lumot topilmadi (eski tizimdagi buyurtma bo'lishi mumkin).", show_alert=True)
        return
        
    try:
        decrypted_data = decrypt_text(row[0])
    except Exception:
        decrypted_data = "Ma'lumotni o'qishda xatolik yuz berdi."
        
    text_msg = (
        f"🧾 <b>Buyurtma:</b> <code>{order.order_number}</code>\n"
        f"💰 <b>Narxi:</b> {format_money(order.price)}\n\n"
        f"🔑 <b>Sizning ma'lumotlaringiz:</b>\n"
        f"<code>{decrypted_data}</code>"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Orqaga", callback_data="profile_orders")
    
    try:
        await callback.message.edit_caption(caption=text_msg, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.edit_text(text=text_msg, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "profile_discounts")
async def show_discounts(callback: CallbackQuery):
    text = (
        "🎁 <b>Chegirmalar</b>\n\n"
        "Hozircha faol chegirmalar mavjud emas.\n\n"
        "Yangi chegirmalar va aksiyalar haqida kanalimizni kuzating!"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Orqaga", callback_data="profile_back_detail")
    builder.adjust(1)

    try:
        await callback.message.edit_caption(caption=text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.edit_text(text=text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "profile_change_lang")
async def ask_language_change(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbek tili", callback_data="setlang_uz")
    builder.button(text="🇷🇺 Русский",     callback_data="setlang_ru")
    builder.button(text="🇬🇧 English",     callback_data="setlang_en")
    builder.button(text="↩️ Orqaga",       callback_data="profile_back_detail")
    builder.adjust(1)

    try:
        await callback.message.edit_caption(
            caption="🌐 <b>Tilni tanlang / Выберите язык / Choose language:</b>",
            reply_markup=builder.as_markup()
        )
    except Exception:
        await callback.message.edit_text(
            text="🌐 <b>Tilni tanlang / Выберите язык / Choose language:</b>",
            reply_markup=builder.as_markup()
        )


@router.callback_query(F.data.startswith("setlang_"))
async def set_language(callback: CallbackQuery, session: AsyncSession, db_user: User):
    lang = callback.data.split("_")[1]
    db_user.language = lang
    await session.commit()

    confirms = {
        "uz": "✅ Til o'zgartirildi: 🇺🇿 O'zbek",
        "ru": "✅ Язык изменён: 🇷🇺 Русский",
        "en": "✅ Language changed: 🇬🇧 English",
    }
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Profilga qaytish",
                   callback_data="profile_back_detail")
    builder.adjust(1)

    try:
        await callback.message.edit_caption(caption=confirms[lang], reply_markup=builder.as_markup())
    except Exception:
        await callback.message.edit_text(text=confirms[lang], reply_markup=builder.as_markup())


@router.callback_query(F.data == "profile_back_detail")
async def profile_back_to_detail(callback: CallbackQuery, session: AsyncSession, db_user: User):
    text = await _build_profile_text(db_user, session)
    keyboard = _get_profile_keyboard()
    try:
        await callback.message.edit_caption(caption=text, reply_markup=keyboard)
    except Exception:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "profile_back")
async def profile_back_main(callback: CallbackQuery):
    from bot.handlers.registration import get_main_menu_keyboard
    from core.config import config
    is_admin = callback.from_user.id == config.ADMIN_ID

    text = (
        "👋 <b>Asosiy menyu</b>\n\n"
        "🛍 <b>ENTELLI STORE</b> — PUBG Mobile UC va o'yin akkauntlari do'koni boti!"
    )
    try:
        await callback.message.edit_caption(caption=text, reply_markup=get_main_menu_keyboard(lambda x: x, is_admin=is_admin))
    except Exception:
        await callback.message.edit_text(text=text, reply_markup=get_main_menu_keyboard(lambda x: x, is_admin=is_admin))
    await callback.answer()
