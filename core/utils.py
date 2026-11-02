from decimal import Decimal

def format_money(amount: Decimal | int | float) -> str:
    """Pul miqdorini probel bilan formatlash (masalan: 36 000 so'm)"""
    return f"{int(amount):,} so'm".replace(",", " ")
