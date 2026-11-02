import asyncio
from sqlalchemy import text
from db.database import engine
from db.models.base import Base
# Import all models to register
from db.models import *

async def run_phase1_migrations():
    async with engine.begin() as conn:
        print("1. Creating order_number_seq sequence...")
        await conn.execute(text("CREATE SEQUENCE IF NOT EXISTS order_number_seq START 1;"))
        
        print("2. Creating balance_transactions table (and any others)...")
        await conn.run_sync(Base.metadata.create_all)
        
        print("3. Generating OPENING balances for existing users...")
        res = await conn.execute(text("SELECT id, balance FROM users WHERE balance > 0"))
        users = res.fetchall()
        for u in users:
            uid, bal = u
            exist = await conn.execute(text("SELECT id FROM balance_transactions WHERE user_id = :uid AND type = 'OPENING'"), {"uid": uid})
            if not exist.fetchone():
                await conn.execute(text("""
                    INSERT INTO balance_transactions (user_id, amount, balance_after, type, created_at)
                    VALUES (:uid, :bal, :bal, 'OPENING', NOW())
                """), {"uid": uid, "bal": bal})
        
        print("Phase 1 Migrations Completed Successfully!")

if __name__ == "__main__":
    asyncio.run(run_phase1_migrations())
