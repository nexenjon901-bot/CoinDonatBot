from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from typing import List
from db.models.product import Category, Product
from core.emojis import create_button


def get_categories_keyboard(categories: List[Category], with_back: bool = True) -> InlineKeyboardMarkup:
    """Kategoriyalar ro'yxati uchun inline klaviatura (Premium emoji bilan)"""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        emoji_key = "pubg"
        builder.add(create_button(cat.name, emoji_key=emoji_key, callback_data=f"shop_cat_{cat.id}"))
    if with_back:
        builder.add(create_button("Orqaga", emoji_key="back", callback_data="menu_back"))
    builder.adjust(1)
    return builder.as_markup()


def get_products_keyboard(products: List[Product], category_id: int) -> InlineKeyboardMarkup:
    """Mahsulotlar ro'yxati uchun inline klaviatura (Premium emoji bilan)"""
    builder = InlineKeyboardBuilder()
    for prod in products:
        is_uc = getattr(prod, "product_type", "account") == "uc"
        emoji_key = "pubg"
        price_uzs = f"{float(prod.price_uzs):,.0f} so'm"

        if is_uc:
            text = f"{prod.name} — {price_uzs}"
        else:
            status = f"{prod.quantity} dona" if prod.quantity > 0 else "Mavjud emas"
            text = f"{prod.name} — {status} — {price_uzs}"

        builder.add(create_button(text, emoji_key=emoji_key, callback_data=f"shop_prod_{prod.id}"))
    builder.add(create_button("Orqaga", emoji_key="back", callback_data="shop_back_cats"))
    builder.adjust(1)
    return builder.as_markup()


def get_product_detail_keyboard(product: Product) -> InlineKeyboardMarkup:
    """Mahsulot batafsil uchun inline klaviatura (Premium emoji bilan)"""
    builder = InlineKeyboardBuilder()
    is_uc = getattr(product, "product_type", "account") == "uc"

    if is_uc or product.quantity > 0:
        builder.add(create_button("Sotib olish", emoji_key="shop", callback_data=f"shop_buy_{product.id}"))
    else:
        builder.add(create_button("Hozircha mavjud emas", emoji_key="cancel", callback_data="shop_noop"))
    builder.add(create_button("Orqaga", emoji_key="back", callback_data=f"shop_back_prod_{product.category_id}"))
    builder.adjust(1)
    return builder.as_markup()


def get_purchase_confirm_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Xarid tasdiqlash uchun klaviatura"""
    builder = InlineKeyboardBuilder()
    builder.add(create_button("Tasdiqlash", emoji_key="verify", callback_data=f"shop_confirm_{product_id}"))
    builder.add(create_button("Bekor qilish", emoji_key="cancel", callback_data=f"shop_back_prod_confirm_{product_id}"))
    builder.adjust(1)
    return builder.as_markup()


def get_uc_confirm_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """UC xarid tasdiqlash uchun klaviatura"""
    builder = InlineKeyboardBuilder()
    builder.add(create_button("Tasdiqlash va to'lash", emoji_key="verify", callback_data=f"shop_uc_confirm_{product_id}"))
    builder.add(create_button("Bekor qilish", emoji_key="cancel", callback_data=f"shop_back_prod_{product_id}"))
    builder.adjust(1)
    return builder.as_markup()
