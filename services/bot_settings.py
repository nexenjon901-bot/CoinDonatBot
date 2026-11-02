from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import config
from db.models.setting import Setting, SettingKeys


async def get_setting(session: AsyncSession, key: str, default: str = "") -> str:
    res = await session.execute(select(Setting).where(Setting.key == key))
    row = res.scalar_one_or_none()
    if row and row.value is not None:
        return row.value
    return default


async def payment_card(session: AsyncSession) -> str:
    return await get_setting(session, SettingKeys.PAYMENT_CARD, config.PAYMENT_CARD)


async def payment_card_owner(session: AsyncSession) -> str:
    return await get_setting(session, SettingKeys.PAYMENT_CARD_OWNER, config.PAYMENT_CARD_OWNER)


async def payment_phone(session: AsyncSession) -> str:
    return await get_setting(session, SettingKeys.PAYMENT_PHONE, getattr(config, "PAYMENT_PHONE", ""))


async def support_url(session: AsyncSession) -> str:
    username = await get_setting(session, SettingKeys.SUPPORT_USERNAME, "")
    if username:
        uname = username.lstrip("@")
        return f"https://t.me/{uname}"
    return getattr(config, "SUPPORT_URL", "https://t.me/entelli_sale")
