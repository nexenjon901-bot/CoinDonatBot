from decimal import Decimal

def format_money(amount: Decimal | int | float) -> str:
    """Pul miqdorini probel bilan formatlash (masalan: 36 000 so'm)"""
    return f"{int(amount):,} so'm".replace(",", " ")


def premium_emoji(emoji_id: str, fallback: str = "🎮") -> str:
    """Telegram Premium (custom) emoji HTML tegi qaytaradi.
    
    Faqat xabar matnlarida ishlaydi (caption, text).
    Inline keyboard tugma matnlarida ISHLAMAYDI — u yerda standart Unicode emoji ishlating.
    
    Misol:
        premium_emoji("5368324170671202286", "💎")
        => '<tg-emoji emoji-id="5368324170671202286">💎</tg-emoji>'
    """
    if not emoji_id:
        return fallback
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def order_status_icon(status_value: str) -> str:
    """Buyurtma holati uchun emoji belgisi qaytaradi"""
    icons = {
        "COMPLETED": "✅",
        "CANCELLED": "❌",
        "REJECTED": "❌",
        "PAYMENT_REVIEW": "⏳",
        "APPROVED": "🔄",
        "PENDING_PAYMENT": "⏳",
        "DELIVERY_FAILED": "⚠️",
    }
    return icons.get(status_value, "❓")


def order_status_label(status_value: str) -> str:
    """Buyurtma holati uchun o'zbek tilidagi matn qaytaradi"""
    labels = {
        "COMPLETED": "✅ Bajarildi",
        "CANCELLED": "❌ Bekor qilindi",
        "REJECTED": "❌ Rad etildi",
        "PAYMENT_REVIEW": "⏳ To'lov tekshirilmoqda",
        "APPROVED": "🔄 Yetkazilmoqda",
        "PENDING_PAYMENT": "⏳ To'lov kutilmoqda",
        "DELIVERY_FAILED": "⚠️ Yetkazishda xatolik",
    }
    return labels.get(status_value, f"❓ {status_value}")
