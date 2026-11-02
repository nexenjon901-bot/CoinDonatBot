from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.filters.admin import IsAdmin
from core.logger import logger
from db.models.order import BalanceRequest, BalanceRequestStatus
from db.models.user import User
from core.utils import format_money
from services.wallet import credit, TransactionType
from sqlalchemy import text

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(F.text == "💰 Balans so'rovlari")
async def list_balance_requests(message: Message, session: AsyncSession):
    result = await session.execute(
        select(BalanceRequest)
        .options(selectinload(BalanceRequest.user))
        .where(BalanceRequest.status == BalanceRequestStatus.PENDING)
        .order_by(BalanceRequest.created_at.asc())
        .limit(1)
    )
    req = result.scalar_one_or_none()

    if not req:
        await message.answer("✅ Hozircha kutayotgan balans so'rovlari yo'q.")
        return

    await _send_balance_request(message, req)


async def _send_balance_request(target, req: BalanceRequest):
    """So'rovni ko'rsatish"""
    user = req.user
    uname = f"@{user.username}" if user.username else f"ID: {user.telegram_id}"

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=f"bal_approve_{req.id}")
    builder.button(text="❌ Rad etish",  callback_data=f"bal_reject_{req.id}")
    builder.adjust(2)

    text = (
        f"💰 <b>Balans so'rovi #{req.id}</b>\n\n"
        f"👤 Foydalanuvchi: {user.first_name or '—'} ({uname})\n"
        f"💵 So'ralgan miqdor: <b>{format_money(req.amount_uzs)}</b>\n"
        f"📅 Sana: {req.created_at.strftime('%d.%m.%Y %H:%M') if req.created_at else '—'}\n\n"
        f"Chek rasmini ko'rish uchun yuqoridagi fotoqarang."
    )

    if isinstance(target, Message):
        if req.receipt_file_id:
            await target.answer_photo(
                photo=req.receipt_file_id,
                caption=text,
                reply_markup=builder.as_markup()
            )
        else:
            await target.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("bal_approve_"))
async def approve_balance(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    req_id = int(callback.data.split("_")[2])
    
    # Atomik tasdiqlash
    res = await session.execute(
        text("UPDATE balance_requests SET status = 'APPROVED' WHERE id = :id AND status = 'PENDING' RETURNING user_id, amount_uzs"),
        {"id": req_id}
    )
    row = res.fetchone()
    
    if not row:
        await callback.answer("❌ So'rov topilmadi yoki allaqachon ko'rib chiqilgan!", show_alert=True)
        return
        
    user_id, amount_uzs = row
    
    # Pulni balansga qo'shish (atomik)
    await credit(session, user_id, amount_uzs, TransactionType.TOPUP, ref_type="request", ref_id=str(req_id))
    
    await session.commit()
    
    user = await session.get(User, user_id)

    # Foydalanuvchiga xabar
    try:
        await bot.send_message(
            user.telegram_id,
            f"✅ <b>Balansingiz to'ldirildi!</b>\n\n"
            f"💰 Qo'shilgan miqdor: <b>{format_money(amount_uzs)}</b>\n"
            f"💳 Joriy balans: <b>{format_money(user.balance)}</b>"
        )
    except Exception:
        logger.exception("Failed to notify user after balance approval")

    uname = f"@{user.username}" if user.username else f"ID: {user.telegram_id}"
    try:
        await callback.message.edit_caption(
            caption=f"✅ <b>Tasdiqlandi!</b>\n\n"
            f"👤 {uname}\n"
            f"💰 +{format_money(amount_uzs)} balansi to'ldirildi."
        )
    except Exception:
        logger.exception("Failed to update callback message after balance approval")
    await callback.answer("✅ Tasdiqlandi!")


@router.callback_query(F.data.startswith("bal_reject_"))
async def reject_balance(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    req_id = int(callback.data.split("_")[2])
    
    res = await session.execute(
        text("UPDATE balance_requests SET status = 'REJECTED' WHERE id = :id AND status = 'PENDING' RETURNING user_id, amount_uzs"),
        {"id": req_id}
    )
    row = res.fetchone()

    if not row:
        await callback.answer("❌ So'rov topilmadi yoki allaqachon ko'rib chiqilgan!", show_alert=True)
        return
        
    user_id, amount_uzs = row
    await session.commit()
    user = await session.get(User, user_id)

    # Foydalanuvchiga xabar
    try:
        await bot.send_message(
            user.telegram_id,
            f"❌ <b>Balans so'rovingiz rad etildi.</b>\n\n"
            f"💰 Miqdor: {format_money(amount_uzs)}\n\n"
            f"Savol bo'lsa, qo'llab-quvvatlash bilan bog'laning."
        )
    except Exception:
        logger.exception("Failed to notify user after balance rejection")

    try:
        await callback.message.edit_caption(
            caption=f"❌ <b>Rad etildi!</b>\n\nFoydalanuvchiga xabar yuborildi."
        )
    except Exception:
        logger.exception("Failed to update callback message after balance rejection")
        await callback.message.edit_text(
            text=f"❌ <b>Rad etildi!</b>\n\nFoydalanuvchiga xabar yuborildi."
        )
    await callback.answer("❌ Rad etildi!")
