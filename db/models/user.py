from sqlalchemy import Column, Integer, String, BigInteger, Numeric, DateTime, Boolean, func
from db.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    phone_number = Column(String(50), nullable=True)
    language = Column(String(10), default="uz")
    is_blocked = Column(Boolean, default=False)

    # Balans tizimi
    balance = Column(Numeric(15, 2), default=0,
                     nullable=False)        # UZS balansi
    total_spent = Column(Numeric(15, 2), default=0,
                         nullable=False)    # Jami sarflangan UZS

    # Referal tizimi
    referral_code = Column(String(20), unique=True, nullable=True, index=True)
    # Kim taklif qilgan (referral_code)
    referred_by = Column(String(20), nullable=True)
    ref_balance = Column(Numeric(15, 2), default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
