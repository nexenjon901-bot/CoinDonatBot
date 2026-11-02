import enum
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import relationship
from db.models.base import Base


class TransactionType(str, enum.Enum):
    TOPUP = "TOPUP"
    PURCHASE = "PURCHASE"
    REFERRAL_BONUS = "REFERRAL_BONUS"
    ADMIN_ADJUST = "ADMIN_ADJUST"
    REFUND = "REFUND"
    OPENING = "OPENING"


class BalanceTransaction(Base):
    __tablename__ = "balance_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    balance_after = Column(Numeric(15, 2), nullable=False)
    type = Column(Enum(TransactionType), nullable=False, index=True)
    ref_type = Column(String(50), nullable=True)  # e.g., 'order', 'request'
    ref_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
