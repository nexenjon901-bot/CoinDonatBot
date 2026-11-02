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
    PAYMENT_CARD = "payment_card"           # Karta raqami
    PAYMENT_CARD_OWNER = "payment_card_owner"  # Karta egasi ismi
    PAYMENT_PHONE = "payment_phone"         # Karta/Uzcard ulanish telefoni
    SUPPORT_USERNAME = "support_username"   # Qo'llab-quvvatlash username
    CHANNEL_LINK = "channel_link"           # Kanal havolasi
    MIN_BALANCE = "min_balance"             # Minimal balans to'ldirish
    REFERRAL_PERCENT = "referral_percent"
    CASHBACK_PERCENT = "cashback_percent"
    MIN_WITHDRAWAL = "min_withdrawal"
