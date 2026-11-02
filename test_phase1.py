import asyncio
import pytest
from decimal import Decimal
from sqlalchemy import text
from db.database import async_session
from db.models import User, Product, Category, BalanceRequest, BalanceRequestStatus, Order
from services.wallet import debit, TransactionType

@pytest.mark.asyncio
async def test_wallet_race_condition_insufficient_funds():
    async with async_session() as session:
        # 1. Setup test user
        res = await session.execute(text("INSERT INTO users (telegram_id, balance, total_spent) VALUES (999999991, 100, 0) RETURNING id"))
        user_id = res.scalar()
        await session.commit()

        # 2. Try to debit 100 concurrently 10 times
        async def try_debit():
            async with async_session() as s:
                try:
                    await debit(s, user_id, Decimal("100"), TransactionType.PURCHASE)
                    await s.commit()
                    return True
                except Exception:
                    await s.rollback()
                    return False

        results = await asyncio.gather(*[try_debit() for _ in range(10)])
        
        # 3. Assert only one succeeded
        successes = sum(results)
        assert successes == 1, f"Expected 1 success, got {successes}"

        # 4. Check balance is exactly 0 and not negative
        user_res = await session.execute(text("SELECT balance FROM users WHERE id = :id"), {"id": user_id})
        assert user_res.scalar() == 0

        # Check transactions sum
        tx_res = await session.execute(text("SELECT sum(amount) FROM balance_transactions WHERE user_id = :id"), {"id": user_id})
        # Note: opening balance wasn't added as transaction in this raw test setup, so it will be -100
        assert tx_res.scalar() == -100

        # Cleanup
        await session.execute(text("DELETE FROM balance_transactions WHERE user_id = :id"), {"id": user_id})
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        await session.commit()

@pytest.mark.asyncio
async def test_stock_race_condition():
    async with async_session() as session:
        res = await session.execute(text("INSERT INTO categories (name) VALUES ('Test') RETURNING id"))
        cat_id = res.scalar()
        res = await session.execute(text("INSERT INTO products (category_id, name, price_uzs, quantity) VALUES (:cid, 'P1', 10, 1) RETURNING id"), {"cid": cat_id})
        prod_id = res.scalar()
        await session.commit()

        async def try_buy():
            async with async_session() as s:
                res = await s.execute(
                    text("UPDATE products SET quantity = quantity - 1 WHERE id = :id AND quantity > 0 RETURNING id"),
                    {"id": prod_id}
                )
                row = res.fetchone()
                if row:
                    await s.commit()
                    return True
                return False

        results = await asyncio.gather(*[try_buy() for _ in range(5)])
        successes = sum(results)
        assert successes == 1, f"Expected 1 success, got {successes}"

        res = await session.execute(text("SELECT quantity FROM products WHERE id = :id"), {"id": prod_id})
        assert res.scalar() == 0

        # Cleanup
        await session.execute(text("DELETE FROM products WHERE id = :id"), {"id": prod_id})
        await session.execute(text("DELETE FROM categories WHERE id = :id"), {"id": cat_id})
        await session.commit()

@pytest.mark.asyncio
async def test_balance_request_double_approve():
    async with async_session() as session:
        res = await session.execute(text("INSERT INTO users (telegram_id, balance, total_spent) VALUES (999999992, 0, 0) RETURNING id"))
        user_id = res.scalar()
        res = await session.execute(text("INSERT INTO balance_requests (user_id, amount_uzs, status) VALUES (:uid, 50, 'PENDING') RETURNING id"), {"uid": user_id})
        req_id = res.scalar()
        await session.commit()

        async def try_approve():
            async with async_session() as s:
                res = await s.execute(
                    text("UPDATE balance_requests SET status = 'APPROVED' WHERE id = :id AND status = 'PENDING' RETURNING user_id, amount_uzs"),
                    {"id": req_id}
                )
                row = res.fetchone()
                if row:
                    # In real code this calls wallet.credit, here we simulate atomic logic check
                    uid, amt = row
                    await s.execute(text("UPDATE users SET balance = balance + :a WHERE id = :uid"), {"a": amt, "uid": uid})
                    await s.commit()
                    return True
                return False

        results = await asyncio.gather(*[try_approve() for _ in range(3)])
        successes = sum(results)
        assert successes == 1, f"Expected 1 success, got {successes}"

        res = await session.execute(text("SELECT balance FROM users WHERE id = :id"), {"id": user_id})
        assert res.scalar() == 50

        # Cleanup
        await session.execute(text("DELETE FROM balance_requests WHERE id = :id"), {"id": req_id})
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        await session.commit()
