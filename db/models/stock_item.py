import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import relationship
from db.models.base import Base


class StockItemStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    SOLD = "SOLD"


class StockItem(Base):
    """Maxfiy ma'lumotlar (login, parol kabi) ombori"""
    __tablename__ = "stock_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Shifrlangan ma'lumot (Fernet)
    data_encrypted = Column(Text, nullable=False)
    
    status = Column(Enum(StockItemStatus), default=StockItemStatus.AVAILABLE, index=True)
    
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    sold_to_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sold_at = Column(DateTime(timezone=True), nullable=True)

    product = relationship("Product")
    order = relationship("Order")
    sold_to = relationship("User")
