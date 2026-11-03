from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Callable

from bot.filters.admin import IsAdmin
from db.models.user import User
from db.models.order import Order, OrderStatus, BalanceRequest, BalanceRequestStatus
from db.models.product import Category, Product

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Admin panel asosiy klaviaturasi — CoinDonatBot uslubi"""
    rows = [
        [KeyboardButton(text="📊 Statistika"),
         KeyboardButton(text="👥 Foydalanuvchilar")],
        [KeyboardButton(text="🛍 Mahsulotlar"),
         KeyboardButton(text="📂 Kategoriyalar")],
        [KeyboardButton(text="💰 Balans so'rovlari"),
         KeyboardButton(text="🛒 Buyurtmalar")],
        [KeyboardButton(text="📢 Xabar yuborish"),
         KeyboardButton(text="⚙️ Sozlamalar")],
        [KeyboardButton(text="⬅️ Bosh menyuga")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


@router.message(Command("admin"))
@router.message(F.text == "⚙️ Admin panel")
async def admin_menu(message: Message):
    await message.answer(
        "⚙ <b>Boshqaruv</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=get_admin_keyboard()
    )


@router.message(F.text == "⬅️ Bosh menyuga")
async def back_to_main(message: Message, _: Callable[[str], str]):
    from bot.handlers.registration import get_main_menu_keyboard
    await message.answer(
        "🏠 <b>Bosh menyuga qaytdingiz.</b>",
        reply_markup=get_main_menu_keyboard(_, is_admin=True)
    )


# ───────────────────────────────────────────
# STATISTIKA
# ───────────────────────────────────────────

@router.message(F.text == "📊 Statistika")
async def show_statistics(message: Message, session: AsyncSession):
    # Foydalanuvchilar
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0

    # Buyurtmalar
    total_orders = (await session.execute(
        select(func.count(Order.id)).where(
            Order.status == OrderStatus.COMPLETED)
    )).scalar() or 0

    # Daromad (Barcha)
    total_revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.price), 0)).where(
            Order.status == OrderStatus.COMPLETED)
    )).scalar() or 0
    
    # Kunlik daromad
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)
    
    daily_rev = (await session.execute(
        select(func.coalesce(func.sum(Order.price), 0)).where(
            Order.status == OrderStatus.COMPLETED, Order.created_at >= day_ago)
    )).scalar() or 0
    
    weekly_rev = (await session.execute(
        select(func.coalesce(func.sum(Order.price), 0)).where(
            Order.status == OrderStatus.COMPLETED, Order.created_at >= week_ago)
    )).scalar() or 0

    # Kutayotgan balans so'rovlari
    pending_balance = (await session.execute(
        select(func.count(BalanceRequest.id)).where(
            BalanceRequest.status == BalanceRequestStatus.PENDING)
    )).scalar() or 0

    # Mahsulotlar
    total_products = (await session.execute(select(func.count(Product.id)))).scalar() or 0

    text = (
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n"
        f"🛒 Bajarilgan buyurtmalar: <b>{total_orders}</b>\n\n"
        f"💰 <b>Daromadlar:</b>\n"
        f"• Kunlik: <b>{float(daily_rev):,.0f} so'm</b>\n"
        f"• Haftalik: <b>{float(weekly_rev):,.0f} so'm</b>\n"
        f"• Jami: <b>{float(total_revenue):,.0f} so'm</b>\n\n"
        f"🛍 Mahsulotlar soni: <b>{total_products}</b>\n"
        f"⏳ Kutayotgan balans so'rovlari: <b>{pending_balance}</b>"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="📜 Tranzaksiyalar tarixi", callback_data="adm_tx_history")
    
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "adm_tx_history")
async def show_tx_history(callback: CallbackQuery, session: AsyncSession):
    from db.models.balance_transaction import BalanceTransaction
    res = await session.execute(
        select(BalanceTransaction).order_by(BalanceTransaction.created_at.desc()).limit(15)
    )
    txs = res.scalars().all()
    
    if not txs:
        await callback.answer("Tranzaksiyalar yo'q.", show_alert=True)
        return
        
    lines = ["📜 <b>Oxirgi 15 ta tranzaksiya:</b>\n"]
    for tx in txs:
        date = tx.created_at.strftime("%d.%m %H:%M") if tx.created_at else ""
        sign = "+" if tx.amount > 0 else ""
        lines.append(f"• <code>{tx.id}</code> | {date} | {tx.type.value} | {sign}{float(tx.amount):,.0f} so'm | User: {tx.user_id}")
        
    await callback.message.answer("\n".join(lines))
    await callback.answer()


# ───────────────────────────────────────────
# FOYDALANUVCHILAR
# ───────────────────────────────────────────

@router.message(F.text == "👥 Foydalanuvchilar")
async def show_users(message: Message, session: AsyncSession):
    result = await session.execute(
        select(User).order_by(User.created_at.desc()).limit(10)
    )
    users = result.scalars().all()

    total = (await session.execute(select(func.count(User.id)))).scalar() or 0

    if not users:
        await message.answer("👥 Foydalanuvchilar yo'q.")
        return

    lines = [
        f"👥 <b>Foydalanuvchilar</b> (jami: {total})\n<i>Oxirgi 10 ta:</i>\n"]
    for u in users:
        uname = f"@{u.username}" if u.username else "—"
        balance = float(u.balance or 0)
        lines.append(
            f"• {u.first_name or '—'} {uname} — {balance:,.0f} so'm — <code>{u.telegram_id}</code>")

    await message.answer("\n".join(lines))
