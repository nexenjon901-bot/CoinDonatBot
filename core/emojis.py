"""
Telegram Premium (Custom Emoji) va UI Ikonkalar boshqaruvi.
Audit hisobotidagi 5-6 sahifalarga to'liq moslashtirilgan.

Telegram Bot API:
- InlineKeyboardButton(..., icon_custom_emoji_id=...):
  Fragment'da username sotib olgan yoki Premium imtiyoziga ega botlar uchun
- <tg-emoji emoji-id="...">{fallback}</tg-emoji>:
  HTML formatidagi xabar matnlari va sarlavhalarida premium emojilarni ko'rsatish
"""

from typing import Optional
from aiogram.types import InlineKeyboardButton
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmojiSettings(BaseSettings):
    # Asosiy menyu va tugmalar custom_emoji_id lari (.env orqali kiritiladi)
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
    EMOJI_SHARE: str = ""        # Ko'k "share" strelkasi
    EMOJI_BACK: str = ""         # Oq burilgan strelka
    EMOJI_VERIFIED: str = ""     # Yashil tasdiq belgisi

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


emojis_cfg = EmojiSettings()

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


def get_emoji_id(key: str) -> Optional[str]:
    """Berilgan kalit bo'yicha custom emoji ID ni olish"""
    mapping = {
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
        "share": emojis_cfg.EMOJI_SHARE,
        "back": emojis_cfg.EMOJI_BACK,
        "verified": emojis_cfg.EMOJI_VERIFIED,
    }
    eid = mapping.get(key, "").strip()
    return eid if eid else None


def format_header_emoji(key: str) -> str:
    """
    Sarlavha va matnlar uchun:
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
    Agar icon_custom_emoji_id qo'llab-quvvatlansa va emoji_id mavjud bo'lsa,
    tugmaga icon biriktiradi. Shuningdek matnga fallback emoji qo'shadi.
    """
    eid = get_emoji_id(emoji_key) if emoji_key else None
    fallback = FALLBACK_ICONS.get(emoji_key, "") if emoji_key else ""

    # Tugma matnida ko'rinadigan qism
    btn_text = f"{fallback} {text}".strip() if fallback and not text.startswith(fallback) else text

    kwargs = {"text": btn_text}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url
    if eid:
        # aiogram / Telegram Bot API icon_custom_emoji_id
        kwargs["icon_custom_emoji_id"] = eid

    return InlineKeyboardButton(**kwargs)
