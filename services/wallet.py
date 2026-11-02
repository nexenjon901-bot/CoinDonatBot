from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from db.models.balance_transaction import TransactionType

class InsufficientFunds(Exception):
    pass

async def credit(session: AsyncSession, user_id: int, amount: Decimal, type_: TransactionType, ref_type: str = None, ref_id: str = None):
    """Atomik ravishda balansni oshirish va jurnalga yozish."""
    if amount <= 0:
        raise ValueError("Amount must be positive")
    
    # Update balance
    result = await session.execute(
        text("UPDATE users SET balance = balance + :amount WHERE id = :user_id RETURNING balance"),
        {"amount": amount, "user_id": user_id}
    )
    row = result.fetchone()
    if not row:
        raise ValueError("User not found")
    
    balance_after = row[0]
    
    # Yozuv (log)
    await session.execute(
        text("""
            INSERT INTO balance_transactions (user_id, amount, balance_after, type, ref_type, ref_id, created_at)
            VALUES (:user_id, :amount, :balance_after, :type, :ref_type, :ref_id, NOW())
        """),
        {
            "user_id": user_id,
            "amount": amount,
            "balance_after": balance_after,
            "type": type_.value,
            "ref_type": ref_type,
            "ref_id": ref_id
        }
    )

async def debit(session: AsyncSession, user_id: int, amount: Decimal, type_: TransactionType, ref_type: str = None, ref_id: str = None):
    """Atomik ravishda balansdan yechish va jurnalga yozish."""
    if amount <= 0:
        raise ValueError("Amount must be positive")
    
    result = await session.execute(
        text("UPDATE users SET balance = balance - :amount WHERE id = :user_id AND balance >= :amount RETURNING balance"),
        {"amount": amount, "user_id": user_id}
    )
    row = result.fetchone()
    if not row:
        raise InsufficientFunds("Not enough balance")
    
    balance_after = row[0]
    
    # UPDATE total_spent (using atomic update too, although it could be done in the same query)
    await session.execute(
        text("UPDATE users SET total_spent = total_spent + :amount WHERE id = :user_id"),
        {"amount": amount, "user_id": user_id}
    )

    await session.execute(
        text("""
            INSERT INTO balance_transactions (user_id, amount, balance_after, type, ref_type, ref_id, created_at)
            VALUES (:user_id, :amount, :balance_after, :type, :ref_type, :ref_id, NOW())
        """),
        {
            "user_id": user_id,
            "amount": -amount,  # Manfiy
            "balance_after": balance_after,
            "type": type_.value,
            "ref_type": ref_type,
            "ref_id": ref_id
        }
    )
