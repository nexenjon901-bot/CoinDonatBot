from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models.order import Order, OrderStatus
from .base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)

    async def get_by_user(self, user_id: int, limit: int = 50) -> List[Order]:
        """Foydalanuvchi buyurtmalarini olish"""
        result = await self.session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_order_number(self, order_number: str) -> Optional[Order]:
        """Buyurtma raqami bo'yicha olish"""
        result = await self.session.execute(
            select(Order).where(Order.order_number == order_number)
        )
        return result.scalar_one_or_none()

    async def get_by_status(self, status: OrderStatus, limit: int = 100) -> List[Order]:
        """Status bo'yicha buyurtmalarni olish"""
        result = await self.session.execute(
            select(Order)
            .where(Order.status == status)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(self, order_id: int, status: OrderStatus) -> Optional[Order]:
        """Buyurtma statusini yangilash"""
        order = await self.get(order_id)
        if order:
            order.status = status
            await self.session.commit()
            await self.session.refresh(order)
        return order
