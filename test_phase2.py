import asyncio
import pytest
from decimal import Decimal
from sqlalchemy import text
from db.database import async_session
from core.security import encrypt_text

@pytest.mark.asyncio
async def test_stock_skip_locked():
    async with async_session() as session:
        # Create user
        res = await session.execute(text("INSERT INTO users (telegram_id, balance, total_spent) VALUES (999999993, 1000, 0) RETURNING id"))
        user_id = res.scalar()
        
        # Create category and product
        res = await session.execute(text("INSERT INTO categories (name) VALUES ('TestCat2') RETURNING id"))
        cat_id = res.scalar()
        res = await session.execute(text("INSERT INTO products (category_id, name, price_uzs, quantity) VALUES (:cid, 'P2', 10, 1) RETURNING id"), {"cid": cat_id})
        prod_id = res.scalar()
        
        # Insert 1 stock item
        enc = encrypt_text("user1:pass1")
        await session.execute(text("INSERT INTO stock_items (product_id, data_encrypted, status) VALUES (:pid, :enc, 'AVAILABLE')"), {"pid": prod_id, "enc": enc})
        await session.commit()
        
        async def try_buy():
            async with async_session() as s:
                # 1. SKIP LOCKED bilan bo'sh stock_item ni qidiramiz
                res_stock = await s.execute(
                    text("""
                        SELECT id, data_encrypted 
                        FROM stock_items 
                        WHERE product_id = :pid AND status = 'AVAILABLE' 
                        FOR UPDATE SKIP LOCKED 
                        LIMIT 1
                    """),
                    {"pid": prod_id}
                )
                stock_row = res_stock.fetchone()
                if stock_row:
                    stock_id = stock_row[0]
                    # Simulating the rest
                    await s.execute(text("UPDATE stock_items SET status = 'SOLD', sold_to_user_id = :uid WHERE id = :sid"), {"uid": user_id, "sid": stock_id})
                    await s.commit()
                    return True
                return False

        # Run 20 concurrent
        results = await asyncio.gather(*[try_buy() for _ in range(20)])
        successes = sum(results)
        
        # Assert only 1 succeeded
        assert successes == 1
        
        # Cleanup
        await session.execute(text("DELETE FROM stock_items WHERE product_id = :pid"), {"pid": prod_id})
        await session.execute(text("DELETE FROM products WHERE id = :pid"), {"pid": prod_id})
        await session.execute(text("DELETE FROM categories WHERE id = :cid"), {"cid": cat_id})
        await session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})
        await session.commit()
