from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Callable

from db.models.account import Account, AccountStatus
from db.models.favorite import Favorite
from bot.keyboards.catalog import get_account_keyboard

router = Router()

@router.message(F.text.in_(["❤️ Favorites", "❤️ Sevimlilar", "❤️ Избранные"]))
async def show_favorites(message: Message, session: AsyncSession, _: Callable[[str], str]):
    user_id = message.from_user.id
    
    # Join Favorites and Accounts
    result = await session.execute(
        select(Account)
        .join(Favorite, Favorite.account_id == Account.id)
        .where(Favorite.user_id == user_id)
        # We only show them if they are still PUBLISHED. 
        # If sold/hidden, we might want to tell them it's unavailable, but for now we just filter.
        .where(Account.status == AccountStatus.PUBLISHED)
    )
    
    favorites = result.scalars().all()
    
    if not favorites:
        await message.answer(_("msg_fav_empty"))
        return
        
    await message.answer(_("msg_fav_header").format(count=len(favorites)))
    
    for acc in favorites:
        text = f"🎮 <b>{acc.title}</b>\n\n"
        text += f"💰 <b>{_('lbl_price')}:</b> {acc.price:,.0f} {acc.currency}\n\n"
        text += f"🆔 #{acc.id}"
        
        await message.answer(text, reply_markup=get_account_keyboard(acc.id, _, is_favorite=True))
