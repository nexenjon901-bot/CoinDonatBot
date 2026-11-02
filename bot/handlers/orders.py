from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Callable

from db.models.order import Order
from db.models.account import Account

router = Router()


@router.message(F.text.in_(["📦 My Orders", "📦 Buyurtmalarim", "📦 Мои заказы"]))
async def show_orders(message: Message, session: AsyncSession, _: Callable[[str], str]):
    user_id = message.from_user.id

    result = await session.execute(
        select(Order, Account)
        .join(Account, Order.account_id == Account.id)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
    )

    orders = result.all()  # returns a list of tuples (Order, Account)

    if not orders:
        await message.answer(_("msg_orders_empty"))
        return

    await message.answer(_("msg_orders_header").format(count=len(orders)))

    for order, acc in orders:
        text = f"🧾 <b>{order.order_number}</b>\n\n"
        text += f"🎮 {acc.title}\n"
        text += f"💰 <b>{_('lbl_price')}:</b> {order.price:,.0f} UZS\n"
        text += f"📊 <b>{_('lbl_status')}:</b> {order.status.value}\n"
        text += f"📅 <b>{_('lbl_date')}:</b> {order.created_at.strftime('%Y-%m-%d %H:%M')}"

        await message.answer(text)
