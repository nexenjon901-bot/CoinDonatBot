from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models.product import Product, Category
from .base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, session: AsyncSession):
        super().__init__(Category, session)

    async def get_active_categories(self) -> List[Category]:
        """Faol kategoriyalarni olish"""
        result = await self.session.execute(
            select(Category)
            .where(Category.is_active == True)
            .order_by(Category.order_index)
        )
        return list(result.scalars().all())


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession):
        super().__init__(Product, session)

    async def get_by_category(self, category_id: int) -> List[Product]:
        """Kategoriya bo'yicha mahsulotlarni olish"""
        result = await self.session.execute(
            select(Product)
            .where(Product.category_id == category_id, Product.is_active == True)
            .order_by(Product.price_uzs)
        )
        return list(result.scalars().all())

    async def get_active_products(self) -> List[Product]:
        """Barcha faol mahsulotlarni olish"""
        result = await self.session.execute(
            select(Product)
            .where(Product.is_active == True)
            .order_by(Product.price_uzs)
        )
        return list(result.scalars().all())

    async def decrease_quantity(self, product_id: int, amount: int = 1) -> Optional[Product]:
        """Mahsulot miqdorini kamaytirish"""
        product = await self.get(product_id)
        if product and product.quantity >= amount:
            product.quantity -= amount
            await self.session.commit()
            await self.session.refresh(product)
        return product
