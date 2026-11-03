from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.models.user import User
from core.config import config

router = Router()


from core.utils import format_money
from services.wallet import credit, TransactionType
from db.models.setting import Setting, SettingKeys

DEFAULT_MIN_WITHDRAWAL = 10000

async def _get_min_withdrawal(session):
    res = await session.execute(select(Setting).where(Setting.key == SettingKeys.MIN_WITHDRAWAL))
    s = res.scalar_one_or_none()
    try:
        return float(s.value) if s else DEFAULT_MIN_WITHDRAWAL
    except Exception:
        return DEFAULT_MIN_WITHDRAWAL

async def _get_setting_val(session, key, default):
    res = await session.execute(select(Setting).where(Setting.key == key))
    s = res.scalar_one_or_none()
    return s.value if s else default

@router.callback_query(F.data == "ref_withdraw")
async def withdraw_referral_bonus(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not db_user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return
    
    min_wd = await _get_min_withdrawal(session)
    ref_bal = float(db_user.ref_balance or 0)
    if ref_bal < min_wd:
        await callback.answer(f"❌ Minimal yechib olish summasi {format_money(min_wd)}!\nSizda: {format_money(ref_bal)}", show_alert=True)
        return
        
    # Atomik ravishda o'tkazish
    from sqlalchemy import text
    res = await session.execute(
        text("UPDATE users SET ref_balance = 0 WHERE id = :uid AND ref_balance >= :min_amt RETURNING ref_balance"),
        {"uid": db_user.id, "min_amt": min_wd}
    )
    row = res.fetchone()
    if not row:
        await callback.answer("❌ Xatolik! Balans yetarli emas.", show_alert=True)
        return
        
    withdrawn = row[0]
    
    # Asosiy balansga qo'shish
    from decimal import Decimal
    await credit(session, db_user.id, Decimal(str(withdrawn)), TransactionType.REFERRAL_BONUS, ref_type="withdrawal", ref_id=str(db_user.id))
    await session.commit()
    
    await callback.answer(f"✅ {format_money(withdrawn)} asosiy balansingizga o'tkazildi!", show_alert=True)
    
    # Sahifani yangilash
    await session.refresh(db_user)
    await show_referral(callback.message, session, db_user)

async def show_referral(message: Message, session: AsyncSession, db_user: User):
    if not db_user:
        await message.answer("❌ Avval ro'yxatdan o'ting: /start")
        return

    if not db_user.referral_code:
        await message.answer("❌ Referal kodingiz mavjud emas. /start bosing.")
        return

    # Fix #1 & #4: use referral_code in link (not telegram_id); count all referred users
    ref_result = await session.execute(
        select(func.count(User.id)).where(User.referred_by == db_user.referral_code)
    )
    ref_count = ref_result.scalar() or 0

    # Fix #4: confirmed count — referred users who have at least one completed order
    from db.models.order import Order
    confirmed_result = await session.execute(
        select(func.count(func.distinct(Order.user_id))).where(
            Order.user_id.in_(
                select(User.id).where(User.referred_by == db_user.referral_code)
            ),
            Order.status == "completed"
        )
    )
    confirmed_count = confirmed_result.scalar() or 0

    bot_username = config.BOT_USERNAME
    # Fix #1: referral link uses referral_code only (already correct in original, confirmed)
    ref_link = f"https://t.me/{bot_username}?start={db_user.referral_code}"

    # Fix #2: exact audit text
    earned = format_money(db_user.ref_balance)
    text = (
        f"🎁 <b>Referal tizimi</b>\n\n"
        f"🔗 <b>Sizning taklif havolangiz:</b>\n"
        f"<code>https://t.me/{bot_username}?start={db_user.referral_code}</code>\n\n"
        f"📊 <b>Statistikangiz:</b>\n"
        f"• Jami takliflar: {ref_count} ta\n"
        f"• Tasdiqlangan: {confirmed_count} ta  \n"
        f"• Ishlangan summa: {earned} so'm\n\n"
        f"<i>Har bir do'stingiz xavfsizlik tekshiruvidan o'tgach hisobingizga bonus beriladi.</i>"
    )

    builder = InlineKeyboardBuilder()

    # Fix #3: "Do'stlarga ulashish" URL button with Telegram share dialog
    share_text = "COIN DONAT BOT orqali PUBG UC va akkauntlar xarid qiling!"
    share_url = f"https://t.me/share/url?url={ref_link}&text={share_text}"
    builder.button(text="↗️ Do'stlarga ulashish", url=share_url)

    if float(db_user.ref_balance or 0) >= await _get_min_withdrawal(session):
        builder.button(text="💳 Asosiy balansga o'tkazish", callback_data="ref_withdraw")

    # Fix #6: back button uses "menu_back" (not "menu_back_main")
    builder.button(text="↩️ Orqaga", callback_data="menu_back")
    builder.adjust(1)

    try:
        if isinstance(message, CallbackQuery):
            await message.message.edit_text(text, reply_markup=builder.as_markup())
        else:
            await message.answer(text, reply_markup=builder.as_markup())
    except Exception:
        try:
            await message.edit_text(text, reply_markup=builder.as_markup())
        except Exception:
            await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "menu_back_main")
async def ref_back_main(callback: CallbackQuery):
    from bot.handlers.registration import get_main_menu_keyboard
    from core.config import config
    is_admin = callback.from_user.id == config.ADMIN_ID
    text = (
        "👋 <b>Asosiy menyu</b>\n\n"
        "<blockquote>Bu PUBG Mobile va o'yin akkauntlari do'koni boti! "
        "Kerakli bo'limni tanlang va qulay xarid qiling.</blockquote>"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard(lambda x: x, is_admin=is_admin))
    except Exception:
        try:
            await callback.message.edit_caption(caption=text, reply_markup=get_main_menu_keyboard(lambda x: x, is_admin=is_admin))
        except Exception:
            pass
    await callback.answer()
