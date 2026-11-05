from core.config import config
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def generate_order_number(session: AsyncSession) -> str:
    """PostgreSQL SEQUENCE yordamida noyob buyurtma raqamini yaratadi (ketma-ketlik bo'lmasa o'zi yaratadi)"""
    current_year = datetime.datetime.now().year

    await session.execute(text("CREATE SEQUENCE IF NOT EXISTS order_number_seq START 1"))

    for _ in range(100):
        result = await session.execute(text("SELECT nextval('order_number_seq')"))
        number = f"{config.ORDER_PREFIX}-{current_year}-{result.scalar():06d}"
        exists = await session.execute(
            text("SELECT 1 FROM orders WHERE order_number = :n"), {"n": number}
        )
        if exists.first() is None:
            return number

    raise RuntimeError("Noyob buyurtma raqamini yaratib bo'lmadi")
