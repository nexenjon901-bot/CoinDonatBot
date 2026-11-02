import asyncio
from sqlalchemy import text
from db.database import engine

async def run_phase3_migrations():
    async with engine.begin() as conn:
        print("Adding ref_balance to users...")
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS ref_balance NUMERIC(15, 2) DEFAULT 0 NOT NULL;"))
        print("Phase 3 migrations done.")

if __name__ == "__main__":
    asyncio.run(run_phase3_migrations())
