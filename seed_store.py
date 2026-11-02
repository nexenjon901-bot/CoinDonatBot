import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())

from sqlalchemy import text
from db.database import async_session


async def main():
    async with async_session() as session:
        await session.execute(
            text("UPDATE products SET is_active = TRUE, quantity = 5 WHERE id IN (1, 3)")
        )
        await session.execute(
            text("UPDATE users SET balance = 100000 WHERE id IN (1, 2, 3, 4)")
        )
        await session.commit()
        print("seed_ok")


if __name__ == "__main__":
    asyncio.run(main())
