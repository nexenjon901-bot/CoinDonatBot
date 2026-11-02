import asyncio
from sqlalchemy import text
from db.database import engine

async def run_phase4_migrations():
    async with engine.begin() as conn:
        print("Adding image_file_id to products...")
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS image_file_id VARCHAR(255);"))
        print("Phase 4 migrations done.")

if __name__ == "__main__":
    asyncio.run(run_phase4_migrations())
