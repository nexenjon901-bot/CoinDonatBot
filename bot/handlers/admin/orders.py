from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from decimal import Decimal

from db.models.order import Order, OrderStatus
from db.models.account import Account, AccountStatus
from db.models.product import Product
from db.models.user import User
from bot.filters.admin import IsAdmin
from core.config import config
from core.utils import format_money
from services.wallet import credit, TransactionType

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(F.text.in_(["🛒 Buyurtmalar", "🛍 Yangi buyurtmalar"]))
async def list_pending_orders(message: Message, session: AsyncSession):
    # Kutilayotgan buyurtmalar (UC buyurtmalari APPROVED yoki PAYMENT_REVIEW holatdagilar)
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.user), selectinload(Order.product), selectinload(Order.payment))
        .where(Order.status.in_([OrderStatus.APPROVED, OrderStatus.PAYMENT_REVIEW]))
        .order_by(Order.created_at.asc())
        .limit(10)
    )
    orders = result.scalars().all()

    if not orders:
        await message.answer("🛒 <b>Kutilayotgan faol buyurtmalar yo'q.</b>\nBarcha buyurtmalar bajarilgan.")
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    for order in orders:
        is_uc = order.player_id is not None or (order.product and getattr(order.product, "product_type", "") == "uc")
        prod_title = order.product.name if order.product else (f"Akkaunt #{order.account_id}" if order.account_id else "Noma'lum")
        buyer = f"@{order.user.username}" if order.user and order.user.username else f"ID: {order.user_id}"

        text_msg = (
            f"🧾 <b>Buyurtma:</b> <code>{order.order_number}</code>\n"
            f"🎮 <b>Mahsulot:</b> {prod_title}\n"
            f"👤 <b>Xaridor:</b> {buyer}\n"
            f"💰 <b>Summa:</b> {format_money(order.price)}\n"
            f"📅 <b>Sana:</b> {order.created_at.strftime('%d.%m.%Y %H:%M') if order.created_at else ''}\n"
        )

        if is_uc:
            text_msg += f"🆔 <b>PUBG Player ID:</b> <code>{order.player_id or 'Kiritilmagan'}</code>\n"
            text_msg += "⚡️ <i>Holati: UC tushirib berilishi kutilmoqda.</i>"
        else:
            text_msg += "⏳ <i>Holati: To'lov/Ma'lumot tekshiruvi.</i>"

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Yetkazildi (Bajarildi)", callback_data=f"adm_uc_done_{order.id}")
        builder.button(text="❌ Bekor qilish (Pulni qaytarish)", callback_data=f"adm_uc_refund_{order.id}")
        builder.adjust(1)

        await message.answer(text_msg, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("adm_uc_done_"))
async def mark_order_done(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    order_id = int(callback.data.split("_")[3])
    order = await session.get(Order, order_id)

    if not order:
        await callback.answer("Buyurtma topilmadi!", show_alert=True)
        return

    if order.status == OrderStatus.COMPLETED:
        await callback.answer("Bu buyurtma allaqachon bajarilgan!", show_alert=True)
        return

    order.status = OrderStatus.COMPLETED
    await session.commit()

    # Foydalanuvchini yuklash
    user = await session.get(User, order.user_id)
    prod = await session.get(Product, order.product_id) if order.product_id else None
    prod_name = prod.name if prod else "Mahsulotingiz"

    # Foydalanuvchiga xushxabar
    if user:
        try:
            msg_user = (
                f"🎉 <b>Xushxabar! Buyurtmangiz bajarildi!</b>\n\n"
                f"🧾 Buyurtma: <code>{order.order_number}</code>\n"
                f"💎 Mahsulot: <b>{prod_name}</b>\n"
            )
            if order.player_id:
                msg_user += f"🆔 Player ID: <code>{order.player_id}</code>\n\n"
                msg_user += "⚡️ UC hisobingizga muvaffaqiyatli tushirildi! O'yinga kirib tekshirishingiz mumkin."
            else:
                msg_user += "\nBuyurtmangiz muvaffaqiyatli yetkazildi!"

            await bot.send_message(user.telegram_id, msg_user)
        except Exception:
            pass

    try:
        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ <b>BAJARILDI — Foydalanuvchiga xabar yuborildi.</b>",
            reply_markup=None
        )
    except Exception:
        pass

    await callback.answer("✅ Buyurtma muvaffaqiyatli bajarildi!")


@router.callback_query(F.data.startswith("adm_uc_refund_"))
async def refund_order(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    order_id = int(callback.data.split("_")[3])
    order = await session.get(Order, order_id)

    if not order:
        await callback.answer("Buyurtma topilmadi!", show_alert=True)
        return

    if order.status in [OrderStatus.CANCELLED, OrderStatus.REJECTED]:
        await callback.answer("Bu buyurtma allaqachon bekor qilingan!", show_alert=True)
        return

    # Foydalanuvchi balansiga pulni qaytarish
    try:
        await credit(
            session=session,
            user_id=order.user_id,
            amount=Decimal(str(order.price)),
            type_=TransactionType.REFUND,
            ref_type="order_refund",
            ref_id=order.order_number
        )
        order.status = OrderStatus.CANCELLED
        await session.commit()
    except Exception as e:
        await session.rollback()
        await callback.answer(f"Xatolik: {str(e)}", show_alert=True)
        return

    # Foydalanuvchini ogohlantirish
    user = await session.get(User, order.user_id)
    if user:
        try:
            msg_user = (
                f"⚠️ <b>Buyurtmangiz bekor qilindi.</b>\n\n"
                f"🧾 Buyurtma: <code>{order.order_number}</code>\n"
                f"💰 <b>{format_money(order.price)}</b> balansingizga to'liq qaytarildi!\n\n"
                f"<i>Sabab: Noto'g'ri Player ID yoki texnik muammo. Iltimos, ma'lumotlarni tekshirib qaytadan xarid qiling yoki qo'llab-quvvatlashga yozing.</i>"
            )
            await bot.send_message(user.telegram_id, msg_user)
        except Exception:
            pass

    try:
        await callback.message.edit_text(
            f"{callback.message.text}\n\n❌ <b>BEKOR QILINDI — Mablag' foydalanuvchi balansiga qaytarildi.</b>",
            reply_markup=None
        )
    except Exception:
        pass

    await callback.answer("❌ Buyurtma bekor qilindi va mablag' qaytarildi!")
