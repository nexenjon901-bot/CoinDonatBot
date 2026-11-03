"""
Telegram Premium (Custom Emoji) va UI Ikonkalar boshqaruvi.
Admin panel orqali dinamik o'zgartiriladi va ma'lumotlar bazasida saqlanadi.

Telegram Bot API:
- InlineKeyboardButton(..., icon_custom_emoji_id=...):
  Fragment'da username sotib olgan yoki bot egasida tegishli imtiyoz bo'lganda tugma ichida
- <tg-emoji emoji-id="...">{fallback}</tg-emoji>:
  HTML formatidagi xabar matnlari, sarlavhalar, detallar va postlarda Telegram Premium emojilarni ko'rsatish
"""

import re
from typing import Optional, Tuple
from aiogram.types import InlineKeyboardButton, Message
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class EmojiSettings(BaseSettings):
    EMOJI_SHOP: str = ""
    EMOJI_PROFILE: str = ""
    EMOJI_BALANCE: str = ""
    EMOJI_USEFUL: str = ""
    EMOJI_REFERRAL: str = ""
    EMOJI_SUPPORT: str = ""
    EMOJI_PUBG: str = ""
    EMOJI_ORDERS: str = ""
    EMOJI_DISCOUNTS: str = ""
    EMOJI_LANG: str = ""
    EMOJI_POST: str = ""
    EMOJI_MONEY: str = ""
    EMOJI_CARD: str = ""
    EMOJI_ID: str = ""
    EMOJI_DATE: str = ""
    EMOJI_STAT: str = ""
    EMOJI_PACKAGE: str = ""
    EMOJI_VERIFY: str = ""
    EMOJI_WARN: str = ""
    EMOJI_BACK: str = ""

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
    "money": "💰",
    "card": "💳",
    "id": "🆔",
    "date": "📅",
    "stat": "📊",
    "package": "📦",
    "verify": "✅",
    "warn": "⚠️",
    "back": "↩️",
    "cancel": "❌",
    "share": "↗️",
    "admin": "⚙️",
    "wave": "👋",
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
    "money": "💰 Narx va Pul",
    "card": "💳 Karta va To'lov",
    "id": "🆔 Foydalanuvchi ID",
    "date": "📅 Sana va Vaqt",
    "stat": "📊 Statistika",
    "package": "📦 Mahsulot / Stok",
    "verify": "✅ Bajarildi / Tasdiq",
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

    env_val = getattr(emojis_cfg, f"EMOJI_{key.upper()}", "")
    return env_val.strip() if env_val else None


def pe(key: str, fallback: Optional[str] = None) -> str:
    """
    Qisqa nom: Premium Emoji (pe).
    Matn ichida va sarlavhalarda Premium Emoji chiqarish uchun asosiy funksiya.
    Agar custom_emoji_id bo'lsa: <tg-emoji emoji-id="...">fallback</tg-emoji>
    Aks holda: standart fallback emoji.
    """
    fb = fallback or FALLBACK_ICONS.get(key, "✨")
    eid = get_emoji_id(key)
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'
    return fb


def format_header_emoji(key: str) -> str:
    return pe(key)


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

    # Agar custom emoji ID mavjud bo'lsa — tugma matniga fallback qo'shmaymiz
    # (Telegram har ikkalasini ko'rsatib, ikki marta emoji chiqaradi)
    # Matn allaqachon emoji bilan boshlansa (masalan kategoriya nomi "🎮 PUBG"),
    # ikkinchi emoji qo'shilmaydi.
    has_leading_symbol = bool(text) and not (text[0].isalnum() or text[0] in "'\"(")
    if eid:
        # icon_custom_emoji_id o'zi ko'rsatadi — matndagi bosh emoji olib tashlanadi
        btn_text = re.sub(r"^[^\w]+", "", text) if has_leading_symbol else text
    elif fallback and not has_leading_symbol:
        btn_text = f"{fallback} {text}".strip()
    else:
        btn_text = text

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
    """
    if message.entities:
        for entity in message.entities:
            if entity.type == "custom_emoji" and entity.custom_emoji_id:
                fallback = message.text[entity.offset: entity.offset + entity.length] if message.text else "✨"
                return str(entity.custom_emoji_id), fallback

    raw_text = (message.text or "").strip()
    if raw_text.isdigit() and len(raw_text) > 10:
        return raw_text, "✨"

    return None, raw_text
