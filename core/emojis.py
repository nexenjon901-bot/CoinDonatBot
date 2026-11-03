"""
Telegram Premium (Custom Emoji) va UI Ikonkalar boshqaruvi.
Admin panel orqali dinamik o'zgartiriladi va ma'lumotlar bazasida saqlanadi.

Telegram Bot API:
- InlineKeyboardButton(..., icon_custom_emoji_id=...):
  Fragment'da username sotib olgan yoki bot egasida tegishli imtiyoz bo'lganda
- <tg-emoji emoji-id="...">{fallback}</tg-emoji>:
  HTML formatidagi xabar matnlari, sarlavhalar va postlarda Telegram Premium emojilarni ko'rsatish
"""

from typing import Optional, Tuple
from aiogram.types import InlineKeyboardButton, Message
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class EmojiSettings(BaseSettings):
    # Standart .env zaxira ID lar
    EMOJI_SHOP: str = ""         # Pushti sumka (shopping bag)
    EMOJI_PROFILE: str = ""      # Ko'k odam silueti (bust)
    EMOJI_BALANCE: str = ""      # Qanotli pul (money with wings)
    EMOJI_USEFUL: str = ""       # Kulrang gazeta
    EMOJI_REFERRAL: str = ""     # Sariq qo'l siqish (handshake)
    EMOJI_SUPPORT: str = ""      # Sariq operator/xodim
    EMOJI_PUBG: str = ""         # PUBG o'yin ikonkasi
    EMOJI_ORDERS: str = ""       # Oq varaq / hujjat
    EMOJI_DISCOUNTS: str = ""    # Ko'k "SALE" / sariq chipta
    EMOJI_LANG: str = ""         # Ko'k-yashil globus
    EMOJI_POST: str = ""         # E'lonlar va postlar ikonkasi
    EMOJI_SHARE: str = ""        # Ko'k "share" strelkasi
    EMOJI_BACK: str = ""         # Oq burilgan strelka
    EMOJI_VERIFIED: str = ""     # Yashil tasdiq belgisi

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


emojis_cfg = EmojiSettings()

# Bazadan yuklangan kesh
_DB_EMOJI_CACHE: dict[str, str] = {}

# Standart (fallback) piktogrammalar
FALLBACK_ICONS = {
    "shop": "🛍",
    "profile": "👤",
    "balance": "💸",
    "useful": "📰",
    "referral": "🤝",
    "support": "👨‍💻",
    "pubg": "🎮",
    "orders": "📄",
    "discounts": "🏷",
    "lang": "🌐",
    "post": "📢",
    "share": "↗️",
    "back": "↩️",
    "cancel": "↩️",
    "verified": "✅",
    "clock": "⏳",
    "warning": "⚠️",
    "card": "💳",
    "diamond": "💎",
    "money": "💰",
}

# Admin paneldagi nomlar
EMOJI_LABELS = {
    "shop": "🛍 Do'kon (Tugma & Sarlavha)",
    "profile": "👤 Profil (Tugma & Sarlavha)",
    "balance": "💸 Hisobni to'ldirish",
    "useful": "📰 Foydali ma'lumotlar",
    "referral": "🤝 Referal tizimi",
    "support": "👨‍💻 Qo'llab-quvvatlash",
    "pubg": "🎮 PUBG Mobile ikonkasi",
    "orders": "📄 Buyurtmalar tarixi",
    "discounts": "🏷 Chegirmalar",
    "lang": "🌐 Bot tili",
    "post": "📢 E'lonlar va Postlar",
}


async def load_emojis_from_db(session: AsyncSession):
    """Bot ishga tushganda yoki yangilanganda DB dan keshga yuklash"""
    from db.models.setting import Setting
    res = await session.execute(select(Setting).where(Setting.key.like("emoji_%")))
    rows = res.scalars().all()
    for row in rows:
        key = row.key.replace("emoji_", "")
        if row.value:
            _DB_EMOJI_CACHE[key] = row.value.strip()


def update_emoji_cache(key: str, emoji_id: str):
    """Keshni tezda yangilash"""
    _DB_EMOJI_CACHE[key] = emoji_id.strip()


def get_emoji_id(key: str) -> Optional[str]:
    """Berilgan kalit bo'yicha custom emoji ID ni olish (avval DB kesh, keyin .env)"""
    if key in _DB_EMOJI_CACHE and _DB_EMOJI_CACHE[key]:
        return _DB_EMOJI_CACHE[key]

    env_mapping = {
        "shop": emojis_cfg.EMOJI_SHOP,
        "profile": emojis_cfg.EMOJI_PROFILE,
        "balance": emojis_cfg.EMOJI_BALANCE,
        "useful": emojis_cfg.EMOJI_USEFUL,
        "referral": emojis_cfg.EMOJI_REFERRAL,
        "support": emojis_cfg.EMOJI_SUPPORT,
        "pubg": emojis_cfg.EMOJI_PUBG,
        "orders": emojis_cfg.EMOJI_ORDERS,
        "discounts": emojis_cfg.EMOJI_DISCOUNTS,
        "lang": emojis_cfg.EMOJI_LANG,
        "post": emojis_cfg.EMOJI_POST,
        "share": emojis_cfg.EMOJI_SHARE,
        "back": emojis_cfg.EMOJI_BACK,
        "verified": emojis_cfg.EMOJI_VERIFIED,
    }
    val = env_mapping.get(key, "").strip()
    return val if val else None


def format_header_emoji(key: str) -> str:
    """
    Sarlavha, matn va postlar uchun:
    Agar custom_emoji_id bo'lsa <tg-emoji> qaytaradi, aks holda standart fallback emoji.
    """
    fallback = FALLBACK_ICONS.get(key, "✨")
    eid = get_emoji_id(key)
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'
    return fallback


def create_button(
    text: str,
    emoji_key: Optional[str] = None,
    callback_data: Optional[str] = None,
    url: Optional[str] = None,
) -> InlineKeyboardButton:
    """
    InlineKeyboardButton yaratish.
    Agar icon_custom_emoji_id bo'lsa biriktiradi, aks holda standart matnli piktogramma.
    """
    eid = get_emoji_id(emoji_key) if emoji_key else None
    fallback = FALLBACK_ICONS.get(emoji_key, "") if emoji_key else ""

    btn_text = f"{fallback} {text}".strip() if fallback and not text.startswith(fallback) else text

    kwargs = {"text": btn_text}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url
    if eid:
        kwargs["icon_custom_emoji_id"] = eid

    return InlineKeyboardButton(**kwargs)


def extract_custom_emoji_id(message: Message) -> Tuple[Optional[str], str]:
    """
    Admin yuborgan xabardan Telegram Premium Custom Emoji ID ni ajratib olish.
    Agar admin Telegram Premium emojini jo'natgan bo'lsa message.entities dan olinadi.
    Agar ID raqamini (5368324170671202286) yozgan bo'lsa o'sha raqam olinadi.
    Qaytaradi: (custom_emoji_id, fallback_text)
    """
    if message.entities:
        for entity in message.entities:
            if entity.type == "custom_emoji" and entity.custom_emoji_id:
                fallback = message.text[entity.offset: entity.offset + entity.length] if message.text else "✨"
                return str(entity.custom_emoji_id), fallback

    # Agar matn faqat raqamlardan iborat bo'lsa (ID bo'lsa)
    raw_text = (message.text or "").strip()
    if raw_text.isdigit() and len(raw_text) > 10:
        return raw_text, "✨"

    return None, raw_text
