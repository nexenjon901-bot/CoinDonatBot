#!/usr/bin/env python3
"""Migration: categories.emoji_id ustunini qo'shamiz"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.database import engine
from sqlalchemy import text


async def migrate():
    async with engine.begin() as conn:
        # emoji_id ustunini qo'shamiz
        await conn.execute(text("""
            ALTER TABLE categories 
            ADD COLUMN IF NOT EXISTS emoji_id VARCHAR(255)
        """))
        print("OK: categories.emoji_id column added (or already exists)")


if __name__ == "__main__":
    asyncio.run(migrate())
