from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from typing import List
from db.models.product import Category, Product


def get_categories_keyboard(categories: List[Category], with_back: bool = True) -> InlineKeyboardMarkup:
    """Kategoriyalar ro'yxati uchun inline klaviatura"""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        emoji = f"{cat.emoji} " if cat.emoji and not cat.name.startswith(cat.emoji) else ""
        builder.button(
            text=f"{emoji}{cat.name}",
            callback_data=f"shop_cat_{cat.id}"
        )
    if with_back:
        builder.button(text="🏠 Orqaga", callback_data="menu_back")
    builder.adjust(1)
    return builder.as_markup()


def get_products_keyboard(products: List[Product], category_id: int) -> InlineKeyboardMarkup:
    """Mahsulotlar ro'yxati uchun inline klaviatura"""
    builder = InlineKeyboardBuilder()
    for prod in products:
        is_uc = getattr(prod, "product_type", "account") == "uc"
        icon = "💎" if is_uc else "🎮"
        price_uzs = f"{float(prod.price_uzs):,.0f} so'm"
        
        if is_uc:
            text = f"{icon} {prod.name} — {price_uzs}"
        else:
            status = f"{prod.quantity} dona" if prod.quantity > 0 else "Mavjud emas"
            text = f"{icon} {prod.name} — {status} — {price_uzs}"
            
        builder.button(
            text=text,
            callback_data=f"shop_prod_{prod.id}"
        )
    builder.button(text="↩️ Orqaga", callback_data="shop_back_cats")
    builder.adjust(1)
    return builder.as_markup()


def get_product_detail_keyboard(product: Product) -> InlineKeyboardMarkup:
    """Mahsulot batafsil uchun inline klaviatura"""
    builder = InlineKeyboardBuilder()
    is_uc = getattr(product, "product_type", "account") == "uc"
    
    # UC uchun quantity cheklovi bo'lmasligi mumkin (admin yoki Midasbuy orqali)
    if is_uc or product.quantity > 0:
        builder.button(text="🛒 Sotib olish",
                       callback_data=f"shop_buy_{product.id}")
    else:
        builder.button(text="❌ Hozircha mavjud emas",
                       callback_data="shop_noop")
    builder.button(text="↩️ Orqaga",
                    callback_data=f"shop_back_prod_{product.category_id}")
    builder.adjust(1)
    return builder.as_markup()


def get_purchase_confirm_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Xarid tasdiqlash uchun klaviatura"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash",
                   callback_data=f"shop_confirm_{product_id}")
    builder.button(text="❌ Bekor qilish",
                   callback_data=f"shop_back_prod_confirm_{product_id}")
    builder.adjust(1)
    return builder.as_markup()


def get_uc_confirm_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """UC xarid tasdiqlash uchun klaviatura"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash va to'lash",
                   callback_data=f"shop_uc_confirm_{product_id}")
    builder.button(text="❌ Bekor qilish",
                   callback_data=f"shop_back_prod_{product_id}")
    builder.adjust(1)
    return builder.as_markup()
