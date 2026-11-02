from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Callable

from db.models.account import Account, AccountStatus
from bot.keyboards.catalog import get_account_keyboard, get_pagination_keyboard
from db.models.favorite import Favorite

router = Router()

# Helper function to get localized strings
# We use aiogram filters to catch texts. Wait, aiogram 3 `F.text` needs exact match, 
# so dynamic translation matching in F is tricky without custom filters. 
# For now, we will handle it via a custom filter or just check against all languages.
# Let's create a custom filter in bot/filters/text_filter.py later. 
# For MVP, let's just use F.text.in_([...])

@router.message(F.text.in_(["🎮 Accounts", "🎮 Akkauntlar", "🎮 Аккаунты"]))
async def show_catalog(message: Message, session: AsyncSession, _: Callable[[str], str]):
    # Fetch first page of PUBLISHED accounts
    limit = 5
    offset = 0
    
    # Query to count total
    total_result = await session.execute(select(func.count(Account.id)).where(Account.status == AccountStatus.PUBLISHED))
    total_accounts = total_result.scalar()
    
    if total_accounts == 0:
        await message.answer(_("msg_catalog_empty"))
        return
        
    total_pages = (total_accounts + limit - 1) // limit
    
    # Fetch accounts
    accounts_result = await session.execute(
        select(Account)
        .where(Account.status == AccountStatus.PUBLISHED)
        .order_by(Account.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    accounts = accounts_result.scalars().all()
    
    await message.answer(_("msg_catalog_header").format(total=total_accounts))
    
    for acc in accounts:
        # Check if favorite
        fav_result = await session.execute(
            select(Favorite).where(
                Favorite.user_id == message.from_user.id,
                Favorite.account_id == acc.id
            )
        )
        is_fav = fav_result.scalar_one_or_none() is not None
        
        text = f"🎮 <b>{acc.title}</b>\n\n"
        text += f"💰 <b>{_('lbl_price')}:</b> {acc.price:,.0f} {acc.currency}\n\n"
        text += f"📝 <b>{_('lbl_desc')}:</b>\n{acc.description[:200]}...\n\n"
        text += f"🆔 #{acc.id}"
        
        # Here we should also handle media (photos/videos). 
        # For simplicity, we just send a text message for now.
        await message.answer(text, reply_markup=get_account_keyboard(acc.id, _, is_fav))
        
    if total_pages > 1:
        await message.answer(_("msg_pagination"), reply_markup=get_pagination_keyboard(1, total_pages))

@router.callback_query(F.data.startswith("cat_page_"))
async def paginate_catalog(callback: CallbackQuery, session: AsyncSession, _: Callable[[str], str]):
    # Extract page and repeat logic.
    await callback.answer("Pagination not fully implemented in this MVP scaffold yet.")

@router.callback_query(F.data.startswith("fav_"))
async def toggle_favorite(callback: CallbackQuery, session: AsyncSession, _: Callable[[str], str]):
    account_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    fav_result = await session.execute(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.account_id == account_id
        )
    )
    fav = fav_result.scalar_one_or_none()
    
    if fav:
        session.delete(fav)
        await session.commit()
        await callback.answer(_("msg_fav_removed"))
    else:
        new_fav = Favorite(user_id=user_id, account_id=account_id)
        session.add(new_fav)
        await session.commit()
        await callback.answer(_("msg_fav_added"))
        
    # We should update the message keyboard here to reflect the new state (heart icon)
    # This requires reconstructing the keyboard and using callback.message.edit_reply_markup
