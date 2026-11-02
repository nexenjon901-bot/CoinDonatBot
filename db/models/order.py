from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum, func, ForeignKey, Text
from sqlalchemy.orm import relationship
from db.models.base import Base
import enum


class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAYMENT_REVIEW = "PAYMENT_REVIEW"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"),
                        nullable=True)       # eski tizim
    product_id = Column(Integer, ForeignKey("products.id"),
                        nullable=True)       # yangi shop tizimi
    product_quantity = Column(Integer, default=1, nullable=False)
    player_id = Column(String(100), nullable=True)          # UC uchun PUBG Player ID
    price = Column(Numeric(15, 2), nullable=False)
    status = Column(Enum(OrderStatus),
                    default=OrderStatus.PENDING_PAYMENT, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    account = relationship("Account")
    product = relationship("Product")
    payment = relationship("Payment", back_populates="order",
                           uselist=False, cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey(
        "orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    method = Column(String(100), nullable=False)
    receipt_file_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="payment")


class BalanceRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class BalanceRequest(Base):
    """Foydalanuvchi balans to'ldirish so'rovlari"""
    __tablename__ = "balance_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # So'ralgan miqdor (UZS)
    amount_uzs = Column(Numeric(15, 2), nullable=False)
    receipt_file_id = Column(String(255), nullable=True)    # Chek rasmi
    status = Column(Enum(BalanceRequestStatus),
                    default=BalanceRequestStatus.PENDING, index=True)
    # Admin izohi (rad etilganda)
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
