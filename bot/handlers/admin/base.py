import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Callable
from datetime import datetime, timedelta, timezone
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.filters.admin import IsAdmin
from db.models.user import User
from db.models.order import Order, OrderStatus, BalanceRequest, BalanceRequestStatus
from db.models.product import Category, Product
from db.models.balance_transaction import BalanceTransaction, TransactionType
from services.wallet import credit, debit
from core.emojis import format_header_emoji

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class AdminStates(StatesGroup):
    waiting_for_user_search = State()
    waiting_for_balance_change = State()
    waiting_for_broadcast_text = State()


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Admin panel asosiy klaviaturasi — CoinDonatBot tartibli uslubi"""
    rows = [
        [KeyboardButton(text="📊 Statistika"),
         KeyboardButton(text="👥 Foydalanuvchilar")],
        [KeyboardButton(text="🛍 Mahsulotlar"),
         KeyboardButton(text="📂 Kategoriyalar")],
        [KeyboardButton(text="💰 Balans so'rovlari"),
         KeyboardButton(text="🛒 Buyurtmalar")],
        [KeyboardButton(text="🌟 Premium Emojilar"),
         KeyboardButton(text="⚙️ Sozlamalar")],
        [KeyboardButton(text="📢 Xabar yuborish"),
         KeyboardButton(text="⬅️ Bosh menyuga")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


@router.message(Command("admin"))
@router.message(F.text == "⚙️ Admin panel")
async def admin_menu(message: Message):
    await message.answer(
        "⚙️ <b>CoinDonatBot Boshqaruv Paneli</b>\n\nKerakli bo'limni tanlang:",
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
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0

    total_orders = (await session.execute(
        select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED)
    )).scalar() or 0

    total_revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.price), 0)).where(Order.status == OrderStatus.COMPLETED)
    )).scalar() or 0

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

    pending_balance = (await session.execute(
        select(func.count(BalanceRequest.id)).where(BalanceRequest.status == BalanceRequestStatus.PENDING)
    )).scalar() or 0

    total_products = (await session.execute(select(func.count(Product.id)))).scalar() or 0

    text = (
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users} ta</b>\n"
        f"🛒 Bajarilgan buyurtmalar: <b>{total_orders} ta</b>\n\n"
        f"💰 <b>Daromadlar:</b>\n"
        f"• Kunlik (24 soat): <b>{float(daily_rev):,.0f} so'm</b>\n"
        f"• Haftalik (7 kun): <b>{float(weekly_rev):,.0f} so'm</b>\n"
        f"• Jami aylanma: <b>{float(total_revenue):,.0f} so'm</b>\n\n"
        f"🛍 Faol mahsulotlar: <b>{total_products} ta</b>\n"
        f"⏳ Kutilayotgan to'lov cheklari: <b>{pending_balance} ta</b>"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="📜 Oxirgi tranzaksiyalar", callback_data="adm_tx_history")
    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "adm_tx_history")
async def show_tx_history(callback: CallbackQuery, session: AsyncSession):
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
        lines.append(f"• #{tx.id} | {date} | {tx.type.value} | {sign}{float(tx.amount):,.0f} so'm | Foydalanuvchi: {tx.user_id}")

    await callback.message.answer("\n".join(lines))
    await callback.answer()


# ───────────────────────────────────────────
# FOYDALANUVCHILAR BOSHQARUVI
# ───────────────────────────────────────────

@router.message(F.text == "👥 Foydalanuvchilar")
async def show_users(message: Message, session: AsyncSession):
    result = await session.execute(
        select(User).order_by(User.created_at.desc()).limit(10)
    )
    users = result.scalars().all()
    total = (await session.execute(select(func.count(User.id)))).scalar() or 0

    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Foydalanuvchi qidirish", callback_data="adm_user_search")
    builder.adjust(1)

    if not users:
        await message.answer("👥 Foydalanuvchilar yo'q.", reply_markup=builder.as_markup())
        return

    lines = [f"👥 <b>Foydalanuvchilar</b> (jami: {total} ta)\n<i>Oxirgi 10 ta ro'yxatdan o'tganlar:</i>\n"]
    for u in users:
        uname = f"@{u.username}" if u.username else "—"
        balance = float(u.balance or 0)
        lines.append(f"• {u.first_name or '—'} ({uname}) — <b>{balance:,.0f} so'm</b> | ID: <code>{u.telegram_id}</code>")

    await message.answer("\n".join(lines), reply_markup=builder.as_markup())


@router.callback_query(F.data == "adm_user_search")
async def start_user_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_user_search)
    await callback.message.answer(
        "🔍 <b>Foydalanuvchini qidirish:</b>\n\n"
        "Foydalanuvchining <b>Telegram ID</b> raqamini yoki <b>@username</b> sini kiriting:\n"
        "(Bekor qilish uchun: /cancel)"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_user_search)
async def process_user_search(message: Message, state: FSMContext, session: AsyncSession):
    query = (message.text or "").strip()
    if query == "/cancel":
        await state.clear()
        await message.answer("❌ Qidiruv bekor qilindi.")
        return

    user = None
    if query.isdigit():
        res = await session.execute(select(User).where(User.telegram_id == int(query)))
        user = res.scalar_one_or_none()
    else:
        clean_user = query.lstrip("@")
        res = await session.execute(select(User).where(User.username.ilike(clean_user)))
        user = res.scalar_one_or_none()

    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi! Qaytadan kiriting yoki /cancel bosing:")
        return

    await state.clear()
    status_str = "🔴 Bloklangan" if user.is_blocked else "🟢 Faol"
    reg_date = user.created_at.strftime("%d.%m.%Y") if user.created_at else "—"

    text = (
        f"👤 <b>Foydalanuvchi profili:</b>\n\n"
        f"• Ism: <b>{user.first_name or '—'}</b>\n"
        f"• Username: @{user.username or '—'}\n"
        f"• Telegram ID: <code>{user.telegram_id}</code>\n"
        f"• Telefon: {user.phone_number or '—'}\n"
        f"• Balans: <b>{float(user.balance or 0):,.0f} so'm</b>\n"
        f"• Keshbek balans: <b>{float(user.ref_balance or 0):,.0f} so'm</b>\n"
        f"• Holat: {status_str}\n"
        f"• Ro'yxatdan o'tgan: {reg_date}"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Balans qo'shish", callback_data=f"adm_usr_add_{user.id}")
    builder.button(text="➖ Balans ayirish", callback_data=f"adm_usr_sub_{user.id}")
    toggle_txt = "🟢 Blokdan chiqarish" if user.is_blocked else "🚫 Bloklash"
    builder.button(text=toggle_txt, callback_data=f"adm_usr_block_{user.id}")
    builder.adjust(2, 1)

    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("adm_usr_block_"))
async def toggle_user_block(callback: CallbackQuery, session: AsyncSession):
    uid = int(callback.data.split("_")[3])
    user = await session.get(User, uid)
    if user:
        user.is_blocked = not user.is_blocked
        await session.commit()
        st = "bloklandi 🔴" if user.is_blocked else "blokdan chiqarildi 🟢"
        await callback.answer(f"Foydalanuvchi {st}!", show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_usr_add_") | F.data.startswith("adm_usr_sub_"))
async def ask_balance_amount(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    action = parts[2]  # add yoki sub
    uid = int(parts[3])

    await state.update_data(target_user_id=uid, balance_action=action)
    await state.set_state(AdminStates.waiting_for_balance_change)

    act_str = "qo'shmoqchi" if action == "add" else "ayirmoqchi"
    await callback.message.answer(
        f"💵 Foydalanuvchiga qancha summa {act_str}siz?\n"
        f"Masalan: <code>50000</code>\n"
        f"(Bekor qilish: /cancel)"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_balance_change)
async def process_balance_change(message: Message, state: FSMContext, session: AsyncSession):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi.")
        return

    text_clean = message.text.replace(" ", "").replace(",", "")
    if not text_clean.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return

    amount = int(text_clean)
    data = await state.get_data()
    uid = data.get("target_user_id")
    action = data.get("balance_action")

    user = await session.get(User, uid)
    if not user:
        await state.clear()
        await message.answer("Foydalanuvchi topilmadi.")
        return

    from decimal import Decimal
    if action == "add":
        await credit(session, user.id, Decimal(str(amount)), TransactionType.ADMIN_ADJUSTMENT, ref_type="admin", ref_id=str(message.from_user.id))
        msg = f"✅ Foydalanuvchi balansi {amount:,} so'mga to'ldirildi!\nYangi balans: <b>{float(user.balance):,.0f} so'm</b>"
    else:
        try:
            await debit(session, user.id, Decimal(str(amount)), TransactionType.ADMIN_ADJUSTMENT, ref_type="admin", ref_id=str(message.from_user.id))
            msg = f"✅ Foydalanuvchi balansidan {amount:,} so'm ayirildi!\nYangi balans: <b>{float(user.balance):,.0f} so'm</b>"
        except Exception:
            msg = "❌ Balans yetarli emas yoki xatolik yuz berdi!"

    await session.commit()
    await state.clear()
    await message.answer(msg)


# ───────────────────────────────────────────
# POST VA E'LON YUBORISH (BROADCAST)
# ───────────────────────────────────────────

@router.message(F.text == "📢 Xabar yuborish")
async def start_broadcast(message: Message, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    post_icon = format_header_emoji("post")
    await message.answer(
        f"{post_icon} <b>Barcha foydalanuvchilarga xabar (post) yuborish</b>\n\n"
        f"Yubormoqchi bo'lgan xabaringizni yozing.\n"
        f"💡 <i>Matnda HTML teglar va Telegram Premium emojilardan erkin foydalanishingiz mumkin!</i>\n\n"
        f"Bekor qilish uchun: /cancel"
    )


@router.message(AdminStates.waiting_for_broadcast_text)
async def process_broadcast(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ E'lon bekor qilindi.")
        return

    await state.clear()
    status_msg = await message.answer("⏳ Xabar barcha foydalanuvchilarga yuborilmoqda...")

    res = await session.execute(select(User.telegram_id).where(User.is_blocked == False))
    user_ids = res.scalars().all()

    sent_count = 0
    fail_count = 0

    for tid in user_ids:
        try:
            await message.copy_to(chat_id=tid)
            sent_count += 1
            await asyncio.sleep(0.05)  # Flood control limit
        except Exception:
            fail_count += 1

    await status_msg.edit_text(
        f"📢 <b>Xabar yuborish yakunlandi!</b>\n\n"
        f"✅ Yetkazildi: <b>{sent_count} ta</b>\n"
        f"❌ Yetkazilmadi (bloklaganlar): <b>{fail_count} ta</b>"
    )
