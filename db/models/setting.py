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
