from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timedelta, timezone
from typing import Callable
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

from db.models.user import User
from db.models.order import Order, OrderStatus
from db.models.product import Product
from core.utils import format_money, premium_emoji, order_status_label

router = Router()

PROFILE_BANNER = "bot/images/profile_v3.png"

# Audit USD rate fix: kurs ≈ 11 880 so'm/$
USD_RATE = 11_880


async def _build_profile_text(db_user: User, session: AsyncSession) -> str:
    """Profil ma'lumotlarini matn sifatida yaratish — CoinDonatBot uslubi"""
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
    joined = db_user.created_at.strftime("%b %d, %Y") if db_user.created_at else "—"

    balance_usd = balance / USD_RATE
    sum24_usd = float(sum24) / USD_RATE
    sum7_usd = float(sum7) / USD_RATE
    sumall_usd = float(sumall) / USD_RATE

    spent_usd = total_spent / USD_RATE

    from core.emojis import pe
    text = (
        f"{pe('profile')} <b>Sizning profilingiz</b>\n\n"
        f"<blockquote>"
        f"• ID: {db_user.telegram_id}\n"
        f"• Username: {username}\n"
        f"• Ro'yxatdan o'tgan: {joined}\n"
        f"• Balans: ${balance_usd:.2f} ({balance:,.0f} so'm)\n"
        f"• Jami sarflangan: ${spent_usd:.2f} ({total_spent:,.0f} so'm)\n\n"
        f"Xaridlar:\n"
        f"• 24 soat: {cnt24} dona / ${sum24_usd:.2f}\n"
        f"• 7 kun: {cnt7} dona / ${sum7_usd:.2f}\n"
        f"• Barcha vaqt: {cntall} dona / ${sumall_usd:.2f}"
        f"</blockquote>"
    )
    return text


def _get_profile_keyboard() -> object:
    """Profil sahifasi uchun inline klaviatura (Telegram Premium emoji bilan)"""
    from core.emojis import create_button
    builder = InlineKeyboardBuilder()
    builder.add(create_button("Buyurtmalar tarixi", emoji_key="orders", callback_data="profile_orders"))
    builder.add(create_button("Chegirmalar", emoji_key="discounts", callback_data="profile_discounts"))
    builder.add(create_button("Bot tili", emoji_key="lang", callback_data="profile_change_lang"))
    builder.add(create_button("Orqaga", emoji_key="back", callback_data="profile_back"))
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

    from core.ui import answer_with_banner
    await answer_with_banner(message, PROFILE_BANNER, text, keyboard)


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

    from core.emojis import create_button, pe
    if not orders:
        text = f"{pe('orders')} <b>Buyurtmalar tarixi</b>\n\nSiz hali hech qanday xarid amalga oshirmagansiz."
    else:
        lines = [f"{pe('orders')} <b>Buyurtmalar tarixi</b>\n\nSo'nggi 10 ta buyurtmangiz:\n"]
        for o in orders:
            date = o.created_at.strftime("%d.%m.%Y") if o.created_at else "—"
            status_val = o.status.value if o.status else ""
            status_icons = {
                "COMPLETED": "✅", "CANCELLED": "❌", "REJECTED": "❌",
                "PAYMENT_REVIEW": "⏳", "APPROVED": "🔄", "PENDING_PAYMENT": "⏳",
                "DELIVERY_FAILED": "⚠️"
            }
            icon = status_icons.get(status_val, "❓")
            lines.append(f"{icon} <code>{o.order_number}</code> — {float(o.price):,.0f} so'm — {date}")
            
            # Har bir buyurtma uchun tugma
            builder.button(text=f"{icon} {o.order_number}", callback_data=f"order_view_{o.id}")
            
        text = "\n".join(lines)

    # 2 ta tugma qatoriga joylashtirish
    builder.adjust(2)
    # Orqaga tugmasi alohida qatorga
    back_row = InlineKeyboardBuilder()
    back_row.add(create_button("Orqaga", emoji_key="back", callback_data="profile_back_detail"))
    builder.attach(back_row)

    from core.ui import show_page
    await show_page(callback, text, builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("order_view_"))
async def view_order_details(callback: CallbackQuery, session: AsyncSession, db_user: User):
    """Buyurtma tafsilotlari — UC va akkaunt buyurtmalarini to'g'ri ko'rsatadi"""
    try:
        order_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("Noto'g'ri buyurtma!", show_alert=True)
        return

    # Buyurtma foydalanuvchiga tegishliligini tekshirish
    order = await session.get(Order, order_id)
    if not order or order.user_id != db_user.id:
        await callback.answer("Buyurtma topilmadi!", show_alert=True)
        return

    from core.security import decrypt_text

    # Mahsulotni yuklaymiz
    prod = await session.get(Product, order.product_id) if order.product_id else None
    prod_name = prod.name if prod else f"Buyurtma #{order.order_number}"

    # UC yoki akkaunt ekanligini aniqlash
    is_uc = False
    if prod and getattr(prod, 'product_type', 'account') == 'uc':
        is_uc = True
    elif order.player_id:
        # Agar player_id mavjud bo'lsa — UC buyurtmasi
        is_uc = True

    # Holat matni
    status_val = order.status.value if order.status else "UNKNOWN"
    status_text = order_status_label(status_val)

    # Narxi va sanasi
    price_str = format_money(order.price)
    date_str = order.created_at.strftime("%d.%m.%Y %H:%M") if order.created_at else "—"

    if is_uc:
        # ═══ UC buyurtmasi — player_id orqali ═══
        player_id_str = order.player_id or "Kiritilmagan"

        # Premium emoji qo'llash (UC uchun 💎)
        uc_icon = premium_emoji("5368324170671202286", "💎")

        text_msg = (
            f"🧾 <b>Buyurtma tafsiloti</b>\n\n"
            f"📌 <b>Raqam:</b> <code>{order.order_number}</code>\n"
            f"{uc_icon} <b>Mahsulot:</b> {prod_name}\n"
            f"🆔 <b>PUBG Player ID:</b> <code>{player_id_str}</code>\n"
            f"💰 <b>Narxi:</b> {price_str}\n"
            f"📅 <b>Sana:</b> {date_str}\n"
            f"📌 <b>Holat:</b> {status_text}\n\n"
            f"<i>UC qo'shilganda holat 'Bajarildi' ga o'zgaradi.</i>"
        )
    else:
        # ═══ Akkaunt buyurtmasi — stock_items dan ═══
        res = await session.execute(
            text("SELECT data_encrypted FROM stock_items WHERE order_id = :oid"),
            {"oid": order_id}
        )
        row = res.fetchone()

        if not row:
            # Eski tizim yoki ma'lumot yo'q
            text_msg = (
                f"🧾 <b>Buyurtma:</b> <code>{order.order_number}</code>\n"
                f"🎮 <b>Mahsulot:</b> {prod_name}\n"
                f"💰 <b>Narxi:</b> {price_str}\n"
                f"📅 <b>Sana:</b> {date_str}\n"
                f"📌 <b>Holat:</b> {status_text}\n\n"
                f"⚠️ <i>Akkaunt ma'lumotlari topilmadi. Admin bilan bog'laning.</i>"
            )
        else:
            try:
                decrypted_data = decrypt_text(row[0])
            except Exception:
                decrypted_data = "Ma'lumotni o'qishda xatolik yuz berdi."

            text_msg = (
                f"🧾 <b>Buyurtma:</b> <code>{order.order_number}</code>\n"
                f"🎮 <b>Mahsulot:</b> {prod_name}\n"
                f"💰 <b>Narxi:</b> {price_str}\n"
                f"📅 <b>Sana:</b> {date_str}\n"
                f"📌 <b>Holat:</b> {status_text}\n\n"
                f"🔑 <b>Akkaunt ma'lumotlari:</b>\n"
                f"<code>{decrypted_data}</code>"
            )

    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Orqaga", callback_data="profile_orders")

    try:
        await callback.message.edit_caption(caption=text_msg, reply_markup=builder.as_markup())
    except Exception:
        try:
            await callback.message.edit_text(text=text_msg, reply_markup=builder.as_markup())
        except Exception:
            await callback.message.answer(text_msg, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "profile_discounts")
async def show_discounts(callback: CallbackQuery):
    from core.emojis import create_button, pe
    from core.ui import show_page

    text = (
        f"{pe('discounts')} <b>Chegirmalar va Promokodlar</b>\n\n"
        "🎁 Hozirda faol aksiyalar mavjud emas.\n"
        "Yangi chegirmalar haqida bot kanalida e'lon qilinadi!"
    )
    builder = InlineKeyboardBuilder()
    builder.add(create_button("Orqaga", emoji_key="back", callback_data="profile_back_detail"))
    await show_page(callback, text, builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "profile_change_lang")
async def ask_language_change(callback: CallbackQuery, db_user: User):
    from core.emojis import create_button, pe
    from core.ui import show_page

    langs = {"uz": "🇺🇿 O'zbekcha", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}
    current = db_user.language if db_user.language in langs else "uz"

    builder = InlineKeyboardBuilder()
    for code, label in langs.items():
        builder.button(text=f"{label} ✅" if code == current else label, callback_data=f"setlang_{code}")
    builder.add(create_button("Orqaga", emoji_key="back", callback_data="profile_back_detail"))
    builder.adjust(1)

    text = (
        f"{pe('lang')} <b>Bot tilini tanlang / Выберите язык / Choose language:</b>\n\n"
        f"Hozirgi til: {langs[current]}"
    )
    await show_page(callback, text, builder.as_markup())
    await callback.answer()


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
    from core.emojis import create_button
    from core.ui import show_page
    builder = InlineKeyboardBuilder()
    builder.add(create_button("Profilga qaytish", emoji_key="back", callback_data="profile_back_detail"))
    await show_page(callback, confirms[lang], builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "profile_back_detail")
async def profile_back_to_detail(callback: CallbackQuery, session: AsyncSession, db_user: User):
    text = await _build_profile_text(db_user, session)
    keyboard = _get_profile_keyboard()
    from core.ui import show_page
    await show_page(callback, text, keyboard, PROFILE_BANNER)
    await callback.answer()


@router.callback_query(F.data == "profile_back")
async def profile_back_main(callback: CallbackQuery):
    from core.ui import show_main_menu
    await show_main_menu(callback)
    await callback.answer()
