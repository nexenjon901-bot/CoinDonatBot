from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Callable
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.models.account import Account, AccountStatus
from db.models.order import Order, OrderStatus, Payment
from bot.states.checkout import Checkout
from services.orders import generate_order_number
from core.config import config

router = Router()

@router.callback_query(F.data.startswith("buy_"))
async def start_checkout(callback: CallbackQuery, state: FSMContext, session: AsyncSession, _: Callable[[str], str]):
    account_id = int(callback.data.split("_")[1])
    
    # Check if account is still available
    acc = await session.get(Account, account_id)
    if not acc or acc.status != AccountStatus.PUBLISHED:
        await callback.answer(_("msg_err_unavailable"), show_alert=True)
        return
        
    # Reserve it so nobody else can buy it simultaneously (optimistic lock logic simplified here)
    acc.status = AccountStatus.RESERVED
    
    # Create Order
    order_num = await generate_order_number(session)
    order = Order(
        order_number=order_num,
        user_id=callback.from_user.id,
        account_id=acc.id,
        price=acc.price,
        status=OrderStatus.PENDING_PAYMENT
    )
    session.add(order)
    await session.commit()
    
    await state.update_data(order_id=order.id)
    
    # Ask for payment method
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Uzcard / Humo", callback_data="pay_card")
    builder.button(text="🏦 Visa / Mastercard", callback_data="pay_visa")
    builder.button(text="❌ " + _("btn_cancel"), callback_data="pay_cancel")
    builder.adjust(1)
    
    text = _("msg_select_payment").format(
        order=order_num,
        price=f"{acc.price:,.0f} {acc.currency}"
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await state.set_state(Checkout.payment_method)


@router.callback_query(Checkout.payment_method, F.data.startswith("pay_"))
async def process_payment_method(callback: CallbackQuery, state: FSMContext, session: AsyncSession, _: Callable[[str], str]):
    method = callback.data.split("_")[1]
    
    data = await state.get_data()
    order_id = data.get("order_id")
    order = await session.get(Order, order_id)
    
    if method == "cancel":
        # Cancel the order, release account
        order.status = OrderStatus.CANCELLED
        acc = await session.get(Account, order.account_id)
        acc.status = AccountStatus.PUBLISHED
        await session.commit()
        await state.clear()
        await callback.message.edit_text(_("msg_order_cancelled"))
        return
        
    await state.update_data(payment_method=method)
    
    # Hardcoded card for MVP. Real app should fetch from DB/Config
    card_info = "8600 1234 5678 9012 (Olimov O.)" if method == "card" else "4266 1234 5678 9012 (Olimov O.)"
    
    text = _("msg_payment_instructions").format(
        method=method.upper(),
        card=card_info,
        price=f"{order.price:,.0f} UZS"
    )
    
    # Provide a cancel button here as well
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ " + _("btn_cancel"), callback_data="pay_cancel")
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await state.set_state(Checkout.receipt_upload)


@router.message(Checkout.receipt_upload, F.photo | F.document)
async def process_receipt(message: Message, state: FSMContext, session: AsyncSession, _: Callable[[str], str]):
    data = await state.get_data()
    order_id = data.get("order_id")
    method = data.get("payment_method")
    
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    
    # Update Order and create Payment record
    order = await session.get(Order, order_id)
    order.status = OrderStatus.PAYMENT_REVIEW
    
    payment = Payment(
        order_id=order.id,
        method=method,
        receipt_file_id=file_id
    )
    session.add(payment)
    await session.commit()
    
    await state.clear()
    
    await message.answer(_("msg_payment_review"))
    
    # Here we should also notify the ADMIN that a new payment requires review.
    # A simple bot.send_message(config.ADMIN_ID, ...) can be added here.
