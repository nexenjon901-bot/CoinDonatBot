import asyncio
from sqlalchemy import text
from db.database import engine
from db.models.base import Base
from db.models import *

async def run_phase2_migrations():
    async with engine.begin() as conn:
        print("1. Creating stock_items table...")
        await conn.run_sync(Base.metadata.create_all)
        
        # O'tish yo'li: Agar mavjud quantity bo'lsa, ularni stock_items ga dummy data bilan yozishimiz mumkin,
        # yoki admin o'zi yangidan kiritishi kutiladi. Bu yerda mavjud quantity'ni nolga tushiramiz, 
        # chunki haqiqiy stock_items yo'q.
        print("2. Resetting products quantity since truth source is now stock_items...")
        await conn.execute(text("UPDATE products SET quantity = 0"))

        print("Phase 2 Migrations Completed Successfully!")

if __name__ == "__main__":
    asyncio.run(run_phase2_migrations())
