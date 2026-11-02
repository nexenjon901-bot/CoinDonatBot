import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def generate_order_number(session: AsyncSession) -> str:
    """Generates a unique order number using PostgreSQL SEQUENCE"""
    current_year = datetime.datetime.now().year
    
    # We assume 'order_number_seq' is created in migrations
    result = await session.execute(text("SELECT nextval('order_number_seq')"))
    seq_val = result.scalar()
    
    return f"ENT-{current_year}-{seq_val:06d}"
