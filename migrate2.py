import asyncio
from sqlalchemy import text
from db.database import engine
from db.models.base import Base
from db.models import *


async def run_migrations2():
    async with engine.begin() as conn:
        print("1. Settings jadvali yaratilmoqda...")
        await conn.run_sync(Base.metadata.create_all)
        print("   OK - Jadvallar yaratildi (yoki mavjud).")

        print("2. Categories jadvaliga emoji ustuni qo'shilmoqda...")
        try:
            await conn.execute(text("ALTER TABLE categories ADD COLUMN IF NOT EXISTS emoji VARCHAR(255)"))
            print("   OK: emoji ustuni qo'shildi.")
        except Exception as e:
            print(f"   SKIP: {str(e)[:80]}")

        # Default sozlamalarni kiritib qo'yish
        print("3. Default sozlamalar qo'shilmoqda...")
        try:
            await conn.execute(text("""
                INSERT INTO settings (key, value) VALUES 
                ('payment_card', '8600 1234 5678 9012'),
                ('payment_card_owner', 'Olimov O.')
                ON CONFLICT (key) DO NOTHING
            """))
            print("   OK: Default sozlamalar kiritildi.")
        except Exception as e:
            print(f"   SKIP: {str(e)[:80]}")

        print("\nMigration 2 muvaffaqiyatli yakunlandi!")

if __name__ == "__main__":
    asyncio.run(run_migrations2())
