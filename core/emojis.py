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
    # ─── Qo'shimcha bo'limlar (botdagi boshqa joylar uchun) ───
    "uc": "💎",
    "receipt": "🧾",
    "pending": "⏳",
    "phone": "📱",
    "add": "➕",
    "minus": "➖",
    "cart": "🛒",
    "pin": "📌",
    "gift": "🎁",
    "folder": "📂",
    "users": "👥",
    "star": "🌟",
    "lightning": "⚡",
    "key": "🔑",
    "cash": "💵",
    "refresh": "🔄",
    "question": "❓",
    "online": "🟢",
    "offline": "🔴",
    "exchange": "💱",
    "delete": "🗑",
    "note": "📝",
    "history": "📜",
    "search": "🔍",
    "tip": "💡",
    "link": "🔗",
    "inbox": "📥",
    "home": "🏠",
    "block": "🚫",
    "party": "🎉",
    "coin": "🪙",
    "sad": "😔",
    "alert": "❗",
    "folderfile": "📁",
}

# Bitta kalitga bir nechta standart emoji bog'lash (admin bitta ID kiritadi — hammasi almashadi)
EMOJI_ALIASES = {
    "back": ["🔙", "⬅️"],
    "share": ["↗"],
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
    "back": "↩️ Orqaga tugmasi",
    "cancel": "❌ Bekor qilish / Xato",
    "warn": "⚠️ Ogohlantirish",
    "share": "↗️ Ulashish / Havola",
    "admin": "⚙️ Admin panel / Sozlamalar",
    "wave": "👋 Salomlashish",
    "uc": "💎 UC mahsulot",
    "receipt": "🧾 Buyurtma / Chek",
    "pending": "⏳ Kutilmoqda",
    "phone": "📱 Telefon",
    "add": "➕ Qo'shish",
    "minus": "➖ Ayirish",
    "cart": "🛒 Savat / Xarid",
    "pin": "📌 Belgi (Raqam, Holat)",
    "gift": "🎁 Sovg'a / Bonus",
    "folder": "📂 Kategoriyalar",
    "users": "👥 Foydalanuvchilar",
    "star": "🌟 Premium / Yulduz",
    "lightning": "⚡ Tezkor",
    "key": "🔑 Kalit / Ma'lumot",
    "cash": "💵 Naqd pul",
    "refresh": "🔄 Yangilash",
    "question": "❓ Noma'lum",
    "online": "🟢 Faol",
    "offline": "🔴 Nofaol",
    "exchange": "💱 Valyuta kursi",
    "delete": "🗑 O'chirish",
    "note": "📝 Tavsif",
    "history": "📜 Tarix",
    "search": "🔍 Qidirish",
    "tip": "💡 Maslahat",
    "link": "🔗 Havola",
    "inbox": "📥 Qabul qilish",
    "home": "🏠 Bosh menyu",
    "block": "🚫 Bloklash",
    "party": "🎉 Tabrik",
    "coin": "🪙 Coin Donat",
    "sad": "😔 Afsus",
    "alert": "❗ Muhim",
    "folderfile": "📁 Papka",
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


# ───────────────────────────────────────────
# Avtomatik premium emoji (barcha xabar va tugmalar uchun)
# ───────────────────────────────────────────

_TG_EMOJI_RE = re.compile(r"(<tg-emoji\b[^>]*>.*?</tg-emoji>)", re.DOTALL)
_rx_cache: tuple = (None, None, {})


def _active_glyphs() -> dict[str, str]:
    """ID o'rnatilgan kalitlarning standart emojilari: {emoji: custom_emoji_id}"""
    active: dict[str, str] = {}
    for key, glyph in FALLBACK_ICONS.items():
        eid = get_emoji_id(key)
        if not eid:
            continue
        for g in [glyph, *EMOJI_ALIASES.get(key, [])]:
            active[g.replace("\ufe0f", "")] = eid
    return active


def _get_matcher():
    """(regex, {emoji: id}) — faqat ID o'rnatilgan emojilar uchun; kesh bilan"""
    global _rx_cache
    active = _active_glyphs()
    signature = tuple(sorted(active.items()))
    if _rx_cache[0] == signature:
        return _rx_cache[1], _rx_cache[2]
    if not active:
        _rx_cache = (signature, None, {})
        return None, {}
    alts = sorted(active, key=len, reverse=True)
    rx = re.compile("(?:" + "|".join(re.escape(a) for a in alts) + ")\ufe0f?")
    _rx_cache = (signature, rx, active)
    return rx, active


def premiumize_text(text: str) -> str:
    """HTML matndagi standart emojilarni <tg-emoji> ga almashtiradi (faqat ID o'rnatilganlarini)"""
    rx, active = _get_matcher()
    if not rx or not text:
        return text

    def _wrap(m):
        eid = active.get(m.group(0).replace("\ufe0f", ""))
        return f'<tg-emoji emoji-id="{eid}">{m.group(0)}</tg-emoji>' if eid else m.group(0)

    parts = _TG_EMOJI_RE.split(text)
    for i in range(0, len(parts), 2):  # juft indekslar — tg-emoji dan tashqari qismlar
        parts[i] = rx.sub(_wrap, parts[i])
    return "".join(parts)


def premiumize_markup(markup):
    """Inline tugma matnidagi bosh emojini icon_custom_emoji_id ga aylantiradi"""
    rx, active = _get_matcher()
    rows = getattr(markup, "inline_keyboard", None)
    if not rx or not rows:
        return markup
    changed = False
    new_rows = []
    for row in rows:
        new_row = []
        for btn in row:
            m = rx.match(btn.text or "")
            rest = (btn.text or "")[m.end():].strip() if m else ""
            eid = active.get(m.group(0).replace("\ufe0f", "")) if m else None
            if eid and rest and not getattr(btn, "icon_custom_emoji_id", None):
                btn = btn.model_copy(update={"text": rest, "icon_custom_emoji_id": eid})
                changed = True
            new_row.append(btn)
        new_rows.append(new_row)
    return markup.model_copy(update={"inline_keyboard": new_rows}) if changed else markup


def _set_attr(obj, name: str, value) -> None:
    try:
        setattr(obj, name, value)
    except Exception:
        obj.__dict__[name] = value


def _is_html(parse_mode) -> bool:
    # None — oddiy matn; Default(...) — botning standart HTML rejimi
    return parse_mode is not None and (not isinstance(parse_mode, str) or parse_mode.upper() == "HTML")


def apply_premium_emojis(method) -> None:
    """Telegram'ga ketayotgan so'rovdagi matn, izoh va tugmalarga premium emojilarni qo'llaydi"""
    if not _get_matcher()[0]:
        return
    if _is_html(getattr(method, "parse_mode", None)):
        for attr in ("text", "caption"):
            value = getattr(method, attr, None)
            if isinstance(value, str) and value:
                new_value = premiumize_text(value)
                if new_value != value:
                    _set_attr(method, attr, new_value)
        media = getattr(method, "media", None)
        caption = getattr(media, "caption", None)
        if isinstance(caption, str) and caption and _is_html(getattr(media, "parse_mode", None)):
            new_caption = premiumize_text(caption)
            if new_caption != caption:
                _set_attr(method, "media", media.model_copy(update={"caption": new_caption}))
    markup = getattr(method, "reply_markup", None)
    if markup is not None and hasattr(markup, "inline_keyboard"):
        new_markup = premiumize_markup(markup)
        if new_markup is not markup:
            _set_attr(method, "reply_markup", new_markup)


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
