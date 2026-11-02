from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from db.models.base import Base


class Category(Base):
    """Mahsulot kategoriyalari (masalan: PUBG Mobile, PUBG Mobile 0.80)"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    # Standart emoji yoki fallback (masalan: 🎮, 💎)
    emoji = Column(String(255), nullable=True)
    # Telegram Premium custom_emoji_id
    emoji_id = Column(String(255), nullable=True)
    # Telegram file_id (banner rasm)
    image_file_id = Column(String(255), nullable=True)
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship(
        "Product", back_populates="category", cascade="all, delete-orphan")


class Product(Base):
    """Mahsulotlar (masalan: 60 UC — $1.00)"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey(
        "categories.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)           # "60 UC"
    price_uzs = Column(Numeric(15, 2), nullable=False)   # 12500.00
    price_usd = Column(Numeric(10, 4), nullable=True)    # 1.0000
    # Mavjud miqdor (0 = mavjud emas)
    quantity = Column(Integer, default=0)
    # "Avtomatik yetkazib berish."
    description = Column(Text, nullable=True)
    image_file_id = Column(String(255), nullable=True)
    product_type = Column(String(50), default="account")  # "account" yoki "uc"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("Category", back_populates="products")
