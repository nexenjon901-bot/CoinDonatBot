from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
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


async def _pending_count(session: AsyncSession) -> int:
    return (await session.execute(
        select(func.count(BalanceRequest.id)).where(BalanceRequest.status == BalanceRequestStatus.PENDING)
    )).scalar() or 0


async def _next_pending(session: AsyncSession):
    result = await session.execute(
        select(BalanceRequest)
        .options(selectinload(BalanceRequest.user))
        .where(BalanceRequest.status == BalanceRequestStatus.PENDING)
        .order_by(BalanceRequest.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _edit_message(callback: CallbackQuery, text: str):
    """Chek rasmli xabar (caption) ham, matnli xabar ham yangilanadi"""
    for edit in (
        lambda: callback.message.edit_caption(caption=text, reply_markup=None),
        lambda: callback.message.edit_text(text=text, reply_markup=None),
    ):
        try:
            await edit()
            return
        except Exception:
            continue
    logger.warning("Balans so'rovi xabarini yangilab bo'lmadi")


async def _show_next_request(callback: CallbackQuery, session: AsyncSession):
    """Ko'rib chiqilgan so'rovdan keyin navbatdagisini avtomatik ko'rsatadi"""
    req = await _next_pending(session)
    if req:
        await _send_balance_request(callback.message, req, await _pending_count(session))
    else:
        await callback.message.answer("✅ <b>Barcha balans so'rovlari ko'rib chiqildi.</b>")


@router.message(F.text == "💰 Balans so'rovlari")
async def list_balance_requests(message: Message, session: AsyncSession):
    req = await _next_pending(session)
    if not req:
        await message.answer("✅ <b>Balans so'rovlari</b>\n\n<blockquote>Hozircha kutayotgan so'rovlar yo'q.</blockquote>")
        return

    await _send_balance_request(message, req, await _pending_count(session))


async def _send_balance_request(target, req: BalanceRequest, pending: int = 1):
    """So'rovni ko'rsatish"""
    user = req.user
    uname = f"@{user.username}" if user.username else f"ID: {user.telegram_id}"

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=f"bal_approve_{req.id}")
    builder.button(text="❌ Rad etish",  callback_data=f"bal_reject_{req.id}")
    builder.adjust(2)

    text = (
        f"💰 <b>Balans so'rovi #{req.id}</b>\n\n"
        f"<blockquote>"
        f"👤 Foydalanuvchi: {user.first_name or '—'} ({uname})\n"
        f"💵 So'ralgan miqdor: <b>{format_money(req.amount_uzs)}</b>\n"
        f"📅 Sana: {req.created_at.strftime('%d.%m.%Y %H:%M') if req.created_at else '—'}\n"
        f"💳 Joriy balans: {format_money(user.balance or 0)}"
        f"</blockquote>\n\n"
        f"⏳ Kutayotgan so'rovlar: <b>{pending} ta</b>"
    )

    if isinstance(target, Message):
        if req.receipt_file_id:
            try:
                await target.answer_photo(
                    photo=req.receipt_file_id,
                    caption=text,
                    reply_markup=builder.as_markup()
                )
                return
            except Exception:
                # chek fayl (hujjat) bo'lsa — hujjat sifatida yuboramiz
                try:
                    await target.answer_document(
                        document=req.receipt_file_id,
                        caption=text,
                        reply_markup=builder.as_markup()
                    )
                    return
                except Exception:
                    logger.exception("Chekni yuborib bo'lmadi")
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
            f"<blockquote>"
            f"💰 Qo'shilgan miqdor: <b>{format_money(amount_uzs)}</b>\n"
            f"💳 Joriy balans: <b>{format_money(user.balance)}</b>"
            f"</blockquote>\n\n"
            f"Xaridlarni boshlashingiz mumkin 🛍"
        )
    except Exception:
        logger.exception("Failed to notify user after balance approval")

    uname = f"@{user.username}" if user.username else f"ID: {user.telegram_id}"
    await _edit_message(
        callback,
        f"✅ <b>So'rov #{req_id} tasdiqlandi</b>\n\n"
        f"<blockquote>👤 {uname}\n💰 +{format_money(amount_uzs)} balansga qo'shildi.</blockquote>",
    )
    await callback.answer("✅ Tasdiqlandi!")
    await _show_next_request(callback, session)


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
            f"❌ <b>Balans so'rovingiz rad etildi</b>\n\n"
            f"<blockquote>💰 Miqdor: <b>{format_money(amount_uzs)}</b>\n"
            f"Chek tasdiqlanmadi yoki ma'lumotlar mos kelmadi.</blockquote>\n\n"
            f"Savol bo'lsa, qo'llab-quvvatlash bilan bog'laning."
        )
    except Exception:
        logger.exception("Failed to notify user after balance rejection")

    await _edit_message(
        callback,
        f"❌ <b>So'rov #{req_id} rad etildi</b>\n\n<blockquote>Foydalanuvchiga xabar yuborildi.</blockquote>",
    )
    await callback.answer("❌ Rad etildi!")
    await _show_next_request(callback, session)
