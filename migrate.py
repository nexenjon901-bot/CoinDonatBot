"""
Yangi ustunlar va jadvallarni qo'shish uchun migration skripti.
Bu skript mavjud ma'lumotlarni o'chirmasdan yangi o'zgarishlarni qo'shadi.

Ishlatish:
    python migrate.py
"""
import asyncio
from sqlalchemy import text
from db.database import engine
from db.models.base import Base
from db.models import *


MIGRATIONS = [
    # Users jadvaliga yangi ustunlar
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS balance NUMERIC(15,2) DEFAULT 0 NOT NULL",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS total_spent NUMERIC(15,2) DEFAULT 0 NOT NULL",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(20) UNIQUE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by VARCHAR(20)",

    # Orders jadvaliga yangi ustunlar
    "ALTER TABLE orders ALTER COLUMN account_id DROP NOT NULL",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS product_id INTEGER REFERENCES products(id)",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS product_quantity INTEGER DEFAULT 1 NOT NULL",
]


async def run_migrations():
    async with engine.begin() as conn:
        # Avval yangi jadvallarni yaratamiz
        print("1. Yangi jadvallar yaratilmoqda (categories, products, balance_requests)...")
        await conn.run_sync(Base.metadata.create_all)
        print("   OK - Yangi jadvallar yaratildi.")

        # Keyin mavjud jadvalga ustunlar qo'shamiz
        print("2. Mavjud jadvalga yangi ustunlar qo'shilmoqda...")
        for sql in MIGRATIONS:
            try:
                await conn.execute(text(sql))
                print(f"   OK: {sql[:70]}...")
            except Exception as e:
                print(f"   SKIP (allaqachon mavjud yoki xato): {str(e)[:80]}")

        print("")
        print("Migration muvaffaqiyatli yakunlandi!")


if __name__ == "__main__":
    asyncio.run(run_migrations())
