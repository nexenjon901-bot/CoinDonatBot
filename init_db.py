import asyncio
from db.database import engine
from db.models.base import Base
# Barcha modellarni import qilamiz (Base.metadata ga registratsiya uchun)
from db.models import *


async def init_db():
    async with engine.begin() as conn:
        print("Creating/updating tables (CREATE IF NOT EXISTS)...")
        # drop_all qilmaymiz — faqat yangi jadvallarni qo'shamiz
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Tables created successfully!")


if __name__ == "__main__":
    asyncio.run(init_db())
