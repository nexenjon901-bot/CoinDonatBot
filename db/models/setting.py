from sqlalchemy import Column, String, Text, DateTime, func
from db.models.base import Base


class Setting(Base):
    """Bot sozlamalari — admin panel orqali boshqariladi"""
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Default sozlamalar kalitlari
class SettingKeys:
    PAYMENT_CARD = "payment_card"                # Karta raqami
    PAYMENT_CARD_OWNER = "payment_card_owner"    # Karta egasi ismi
    PAYMENT_PHONE = "payment_phone"              # Karta/Uzcard ulanish telefoni
    SUPPORT_USERNAME = "support_username"        # Qo'llab-quvvatlash username
    SUPPORT_URL = "support_url"                  # Qo'llab-quvvatlash havolasi
    CHANNEL_LINK = "channel_link"                # Chegirmalar kanal havolasi
    MIN_BALANCE = "min_balance"                  # Minimal balans to'ldirish
    USD_RATE = "usd_rate"                        # USD kursi (so'm)
    REFERRAL_PERCENT = "referral_percent"        # Referal foizi (%)
    CASHBACK_PERCENT = "cashback_percent"        # Keshbek foizi (%)
    MIN_WITHDRAWAL = "min_withdrawal"            # Minimal yechib olish summasi

    # Telegram Premium Custom Emoji kalitlari (Admin panel orqali sozlanadi)
    EMOJI_SHOP = "emoji_shop"                    # Do'kon tugmasi / sarlavhasi
    EMOJI_PROFILE = "emoji_profile"              # Profil tugmasi / sarlavhasi
    EMOJI_BALANCE = "emoji_balance"              # To'ldirish tugmasi / sarlavhasi
    EMOJI_USEFUL = "emoji_useful"                # Foydali tugmasi / sarlavhasi
    EMOJI_REFERRAL = "emoji_referral"            # Referal tizimi
    EMOJI_SUPPORT = "emoji_support"              # Qo'llab-quvvatlash
    EMOJI_PUBG = "emoji_pubg"                    # PUBG Mobile
    EMOJI_ORDERS = "emoji_orders"                # Buyurtmalar tarixi
    EMOJI_DISCOUNTS = "emoji_discounts"          # Chegirmalar
    EMOJI_LANG = "emoji_lang"                    # Bot tili
    EMOJI_POST = "emoji_post"                    # E'lonlar / Postlar sarlavhasi
