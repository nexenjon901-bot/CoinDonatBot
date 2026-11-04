from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Callable
import os
from decimal import Decimal

from core.utils import format_money
from services.wallet import debit, TransactionType, InsufficientFunds
from sqlalchemy import text

from db.models.product import Category, Product
from db.models.user import User
from db.models.order import Order, OrderStatus
from bot.states.checkout import UCCheckout
from bot.keyboards.shop import (
    get_categories_keyboard,
    get_products_keyboard,
    get_product_detail_keyboard,
    get_purchase_confirm_keyboard,
    get_uc_confirm_keyboard,
)
from services.orders import generate_order_number

router = Router()

SHOP_BANNER = "bot/images/shop.png"
PRODUCT_BANNER = "bot/images/product_detail.png"


def _shop_text() -> str:
    from core.emojis import pe
    return (
        f"{pe('shop')} <b>Do'kon</b>\n\n"
        "<blockquote>Mahsulotni tanlang — to'lov to'g'ridan-to'g'ri\n"
        "balansingizdan yechiladi va ma'lumotlar bir lahzada beriladi.</blockquote>"
    )


async def _get_banner(path: str):
    """Rasm fayli mavjud bo'lsa FSInputFile, aks holda None"""
    if os.path.exists(path):
        return FSInputFile(path)
    return None


# ───────────────────────────────────────────
# DO'KON — Asosiy sahifa (kategoriyalar)
# ───────────────────────────────────────────

async def show_shop(message: Message, session: AsyncSession, db_user: User, _: Callable[[str], str]):
    cats_result = await session.execute(
        select(Category).where(Category.is_active ==
                               True).order_by(Category.order_index)
    )
    categories = cats_result.scalars().all()

    if not categories:
        await message.answer(
            "😔 <b>Do'kon</b>\n\nHozircha mahsulotlar mavjud emas.\nTez orada qo'shiladi!",
        )
        return

    keyboard = get_categories_keyboard(categories, with_back=True)

    from core.ui import answer_with_banner
    await answer_with_banner(message, SHOP_BANNER, _shop_text(), keyboard)


@router.callback_query(F.data == "shop_back_cats")
async def back_to_categories(callback: CallbackQuery, session: AsyncSession):
    cats_result = await session.execute(
        select(Category).where(Category.is_active ==
                               True).order_by(Category.order_index)
    )
    categories = cats_result.scalars().all()
    keyboard = get_categories_keyboard(categories, with_back=True)

    from core.ui import show_page
    await show_page(callback, _shop_text(), keyboard, SHOP_BANNER)
    await callback.answer()


# ───────────────────────────────────────────
# KATEGORIYA — Mahsulotlar ro'yxati
# ───────────────────────────────────────────

@router.callback_query(F.data.startswith("shop_cat_"))
async def show_category_products(callback: CallbackQuery, session: AsyncSession):
    cat_id = int(callback.data.split("_")[2])

    cat = await session.get(Category, cat_id)
    if not cat:
        await callback.answer("Kategoriya topilmadi!", show_alert=True)
        return

    prods_result = await session.execute(
        select(Product)
        .where(Product.category_id == cat_id, Product.is_active == True)
        .order_by(Product.price_uzs)
    )
    products = prods_result.scalars().all()

    keyboard = get_products_keyboard(products, cat_id)

    from core.ui import show_page
    await show_page(callback, _shop_text(), keyboard, SHOP_BANNER)
    await callback.answer()


# ───────────────────────────────────────────
# MAHSULOT — Batafsil ma'lumot
# ───────────────────────────────────────────

@router.callback_query(F.data.startswith("shop_prod_"))
async def show_product_detail(callback: CallbackQuery, session: AsyncSession):
    prod_id = int(callback.data.split("_")[2])
    prod = await session.get(Product, prod_id)

    if not prod:
        await callback.answer("Mahsulot topilmadi!", show_alert=True)
        return

    from core.ui import USD_RATE
    price_usd = f"${float(prod.price_usd) if prod.price_usd else float(prod.price_uzs) / USD_RATE:.2f}"
    status_text = f"{prod.quantity} dona"
    description = prod.description or "Avtomatik yetkazib berish."

    from core.emojis import pe
    text = (
        f"{pe('pubg')} <b>{prod.name}</b>\n\n"
        f"<blockquote>"
        f"{pe('money')} Narxi: {prod.price_uzs:,.0f} so'm ({price_usd})\n"
        f"{pe('package')} Mavjud: {status_text}\n"
        f"{pe('useful')} Tavsif: {description}"
        f"</blockquote>\n\n"
        f"<i>Xarid qilish uchun quyidagi tugmani bosing:</i>"
    )

    keyboard = get_product_detail_keyboard(prod)

    from core.ui import show_page
    await show_page(callback, text, keyboard, SHOP_BANNER)
    await callback.answer()


@router.callback_query(F.data.startswith("shop_back_prod_"))
async def back_to_product_list(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split("_")
    # shop_back_prod_{cat_id} va shop_back_prod_confirm_{prod_id} ni ajratamiz
    if parts[3] == "confirm":
        prod_id = int(parts[4])
        prod = await session.get(Product, prod_id)
        cat_id = prod.category_id if prod else 1
    else:
        cat_id = int(parts[3])

    prods_result = await session.execute(
        select(Product)
        .where(Product.category_id == cat_id, Product.is_active == True)
        .order_by(Product.price_uzs)
    )
    products = prods_result.scalars().all()

    keyboard = get_products_keyboard(products, cat_id)

    from core.ui import show_page
    await show_page(callback, _shop_text(), keyboard, SHOP_BANNER)
    await callback.answer()


# ───────────────────────────────────────────
# XARID — Tasdiqlash va bajarish
# ───────────────────────────────────────────

@router.callback_query(F.data.startswith("shop_buy_"))
async def start_purchase(callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User):
    prod_id = int(callback.data.split("_")[2])
    prod = await session.get(Product, prod_id)

    if not prod or not prod.is_active:
        await callback.answer("❌ Mahsulot mavjud emas!", show_alert=True)
        return

    is_uc = getattr(prod, "product_type", "account") == "uc"

    if not is_uc and prod.quantity <= 0:
        await callback.answer("❌ Afsuski, hozircha stokda yo'q!", show_alert=True)
        return

    balance = db_user.balance or Decimal('0')
    price = prod.price_uzs
    price_usd = f"${prod.price_usd:.2f}" if prod.price_usd else ""

    if balance < price:
        needed = price - balance
        await callback.answer(
            f"❌ Balansingiz yetarli emas!\n"
            f"Balans: {format_money(balance)}\n"
            f"Kerak: {format_money(price)}\n"
            f"Yetishmaydi: {format_money(needed)}\n\n"
            f"Balansni to'ldiring!",
            show_alert=True
        )
        return

    if is_uc:
        await state.update_data(prod_id=prod.id)
        await state.set_state(UCCheckout.waiting_for_player_id)
        msg_text = (
            f"💎 <b>{prod.name}</b> xaridi\n\n"
            f"💰 Narxi: <b>{format_money(price)} ({price_usd})</b>\n"
            f"💳 Balansingiz: <b>{format_money(balance)}</b>\n\n"
            f"🎮 <b>PUBG Mobile Player ID raqamingizni yuboring:</b>\n"
            f"<i>(Masalan: 5123456789)</i>\n\n"
            f"❌ Bekor qilish uchun: /cancel"
        )
        try:
            await callback.message.edit_caption(caption=msg_text, reply_markup=None)
        except Exception:
            await callback.message.edit_text(text=msg_text, reply_markup=None)
        await callback.answer()
        return

    text = (
        f"🛍 <b>Xarid tasdiqlash</b>\n\n"
        f"🎮 <b>{prod.name}</b>\n"
        f"💰 Narxi: <b>{format_money(price)} ({price_usd})</b>\n"
        f"💳 Sizning balansingiz: <b>{format_money(balance)}</b>\n\n"
        f"Xaridni tasdiqlaysizmi?"
    )

    keyboard = get_purchase_confirm_keyboard(prod_id)
    try:
        await callback.message.edit_caption(caption=text, reply_markup=keyboard)
    except Exception:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()


@router.message(UCCheckout.waiting_for_player_id)
async def process_player_id(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Xarid bekor qilindi.")
        return

    player_id = message.text.strip()
    if not player_id.isdigit() or len(player_id) < 5 or len(player_id) > 16:
        await message.answer("⚠️ <b>Noto'g'ri Player ID!</b>\n\nIltimos, PUBG Mobile Player ID raqamingizni to'g'ri kiriting (faqat raqamlar, 5-16 xonali):\nBekor qilish uchun: /cancel")
        return

    data = await state.get_data()
    prod_id = data.get("prod_id")
    prod = await session.get(Product, prod_id)
    if not prod:
        await state.clear()
        await message.answer("❌ Mahsulot topilmadi.")
        return

    await state.update_data(player_id=player_id)
    balance = db_user.balance or Decimal('0')
    price = prod.price_uzs

    confirm_text = (
        f"💎 <b>UC Xaridini tasdiqlash</b>\n\n"
        f"🎮 Mahsulot: <b>{prod.name}</b>\n"
        f"🆔 PUBG Player ID: <code>{player_id}</code>\n"
        f"💰 Narxi: <b>{format_money(price)}</b>\n"
        f"💳 Sizning balansingiz: <b>{format_money(balance)}</b>\n\n"
        f"⚠️ <i>Player ID to'g'ri kiritilganiga ishonch hosil qiling!</i>\n\n"
        f"Xaridni tasdiqlaysizmi?"
    )

    await message.answer(confirm_text, reply_markup=get_uc_confirm_keyboard(prod.id))


@router.callback_query(F.data.startswith("shop_uc_confirm_"))
async def confirm_uc_purchase(callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User):
    data = await state.get_data()
    player_id = data.get("player_id")
    prod_id = int(callback.data.split("_")[3])
    prod = await session.get(Product, prod_id)

    if not prod or not prod.is_active:
        await state.clear()
        await callback.answer("❌ Mahsulot mavjud emas!", show_alert=True)
        return

    if not player_id:
        await state.clear()
        await callback.answer("❌ Player ID topilmadi, qaytadan urinib ko'ring!", show_alert=True)
        return

    price = prod.price_uzs
    order_num = await generate_order_number(session)

    # 1. Pulni yechamiz
    try:
        await debit(session, db_user.id, price, TransactionType.PURCHASE, ref_type="order", ref_id=order_num)
    except InsufficientFunds:
        await session.rollback()
        await state.clear()
        await callback.answer("❌ Balansingiz yetarli emas!", show_alert=True)
        return
    except Exception:
        await session.rollback()
        await state.clear()
        await callback.answer("❌ Tizimda xatolik yuz berdi!", show_alert=True)
        return

    # 2. Buyurtma yaratamiz
    order = Order(
        order_number=order_num,
        user_id=db_user.id,
        product_id=prod_id,
        product_quantity=1,
        player_id=player_id,
        price=price,
        status=OrderStatus.APPROVED,  # Admin yetkazib berishi kutilmoqda
    )
    session.add(order)
    await session.flush()

    # 3. Cashback va referal
    from db.models.setting import Setting, SettingKeys
    async def get_setting_float(key, default):
        res = await session.execute(select(Setting).where(Setting.key == key))
        s = res.scalar_one_or_none()
        try:
            return float(s.value) if s else default
        except Exception:
            return default

    cb_pct = await get_setting_float(SettingKeys.CASHBACK_PERCENT, 1.0)
    ref_pct = await get_setting_float(SettingKeys.REFERRAL_PERCENT, 2.0)

    buyer_cb = Decimal(str(price)) * Decimal(str(cb_pct / 100))
    if buyer_cb > 0:
        await session.execute(
            text("UPDATE users SET ref_balance = ref_balance + :cb WHERE id = :uid"),
            {"cb": buyer_cb, "uid": db_user.id}
        )

    if db_user.referred_by:
        referrer_cb = Decimal(str(price)) * Decimal(str(ref_pct / 100))
        if referrer_cb > 0:
            await session.execute(
                text("UPDATE users SET ref_balance = ref_balance + :cb WHERE referral_code = :ref"),
                {"cb": referrer_cb, "ref": db_user.referred_by}
            )

    await session.commit()
    await session.refresh(db_user)
    await state.clear()

    # 4. Foydalanuvchiga xabar
    text_msg = (
        f"✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
        f"🧾 Buyurtma: <code>{order_num}</code>\n"
        f"💎 Mahsulot: <b>{prod.name}</b>\n"
        f"🆔 Player ID: <code>{player_id}</code>\n"
        f"💰 To'landi: <b>{format_money(price)}</b>\n\n"
        f"⚡️ <b>UC tez orada hisobingizga tushiriladi!</b>\n"
        f"💳 Qolgan balans: <b>{format_money(db_user.balance)}</b>"
    )

    try:
        await callback.message.edit_text(text=text_msg, reply_markup=None)
    except Exception:
        try:
            await callback.message.edit_caption(caption=text_msg, reply_markup=None)
        except Exception:
            await callback.message.answer(text=text_msg)

    # 5. Adminga xabar va boshqaruv tugmalari
    from aiogram import Bot
    from core.config import config as _config
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    bot: Bot = callback.bot
    buyer = f"@{db_user.username}" if db_user.username else f"ID: {db_user.telegram_id}"
    admin_text = (
        f"⚡️ <b>YANGI UC BUYURTMASI!</b>\n\n"
        f"🧾 Buyurtma: <code>{order_num}</code>\n"
        f"💎 Mahsulot: <b>{prod.name}</b>\n"
        f"🆔 <b>Player ID:</b> <code>{player_id}</code>\n"
        f"👤 Xaridor: {buyer}\n"
        f"💰 Summa: <b>{format_money(price)}</b>\n\n"
        f"❗️ Iltimos, UC ni o'yinchiga tushirib bering va tasdiqlang."
    )

    adm_builder = InlineKeyboardBuilder()
    adm_builder.button(text="✅ Yetkazildi (Bajarildi)", callback_data=f"adm_uc_done_{order.id}")
    adm_builder.button(text="❌ Bekor qilish (Pulni qaytarish)", callback_data=f"adm_uc_refund_{order.id}")
    adm_builder.adjust(1)

    try:
        await bot.send_message(_config.ADMIN_ID, admin_text, reply_markup=adm_builder.as_markup())
        if _config.ORDERS_CHANNEL_ID:
            await bot.send_message(_config.ORDERS_CHANNEL_ID, admin_text)
    except Exception:
        pass


@router.callback_query(F.data.startswith("shop_confirm_"))
async def confirm_purchase(callback: CallbackQuery, session: AsyncSession, db_user: User):
    prod_id = int(callback.data.split("_")[2])
    
    # Order number generation
    order_num = await generate_order_number(session)

    # 1. SKIP LOCKED bilan bo'sh stock_item ni qidiramiz va bloklaymiz
    res_stock = await session.execute(
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
    if not stock_row:
        await callback.answer("❌ Kechirasiz, mahsulot aynan hozir tugab qoldi!", show_alert=True)
        return
    
    stock_id, data_encrypted = stock_row
    
    # 2. Mahsulot nomi va narxini olish
    res_prod = await session.execute(
        text("SELECT name, price_uzs FROM products WHERE id = :id"),
        {"id": prod_id}
    )
    prod_name, price = res_prod.fetchone()
    
    # 3. Atomik ravishda pulni yechamiz
    try:
        await debit(session, db_user.id, price, TransactionType.PURCHASE, ref_type="order", ref_id=order_num)
    except InsufficientFunds:
        await session.rollback()
        await callback.answer("❌ Balansingiz yetarli emas!", show_alert=True)
        return
    except Exception as e:
        await session.rollback()
        await callback.answer("❌ Tizimda xatolik yuz berdi!", show_alert=True)
        return

    # 4. Order yaratamiz
    order = Order(
        order_number=order_num,
        user_id=db_user.id,
        product_id=prod_id,
        product_quantity=1,
        price=price,
        status=OrderStatus.COMPLETED,
    )
    session.add(order)
    await session.flush()
    
    # 5. StockItem ni sotilgan deb belgilash
    await session.execute(
        text("""
            UPDATE stock_items 
            SET status = 'SOLD', order_id = :oid, sold_to_user_id = :uid, sold_at = NOW() 
            WHERE id = :sid
        """),
        {"oid": order.id, "uid": db_user.id, "sid": stock_id}
    )
    
    # 6. Product qoldig'ini yangilash (denormalizatsiya)
    await session.execute(
        text("UPDATE products SET quantity = quantity - 1 WHERE id = :pid"),
        {"pid": prod_id}
    )

    # 7. Cashback (Dynamic from settings)
    from decimal import Decimal
    from db.models.setting import Setting, SettingKeys
    
    async def get_setting_float(key, default):
        res = await session.execute(select(Setting).where(Setting.key == key))
        s = res.scalar_one_or_none()
        try:
            return float(s.value) if s else default
        except Exception:
            return default
            
    cb_pct = await get_setting_float(SettingKeys.CASHBACK_PERCENT, 1.0)
    ref_pct = await get_setting_float(SettingKeys.REFERRAL_PERCENT, 2.0)
    
    buyer_cb = Decimal(str(price)) * Decimal(str(cb_pct / 100))
    if buyer_cb > 0:
        await session.execute(
            text("UPDATE users SET ref_balance = ref_balance + :cb WHERE id = :uid"),
            {"cb": buyer_cb, "uid": db_user.id}
        )
        
    if db_user.referred_by:
        referrer_cb = Decimal(str(price)) * Decimal(str(ref_pct / 100))
        if referrer_cb > 0:
            await session.execute(
                text("UPDATE users SET ref_balance = ref_balance + :cb WHERE referral_code = :ref"),
                {"cb": referrer_cb, "ref": db_user.referred_by}
            )

    await session.commit()
    await session.refresh(db_user)

    # 8. Shifrdan yechish
    from core.security import decrypt_text
    try:
        decrypted_data = decrypt_text(data_encrypted)
    except Exception:
        decrypted_data = "Ma'lumotni o'qishda xatolik. Admin bilan bog'laning."
        # Optionally update order status to DELIVERY_FAILED here
        
    text_msg = (
        f"✅ <b>Xarid muvaffaqiyatli!</b>\n\n"
        f"🧾 Buyurtma: <code>{order_num}</code>\n"
        f"🎮 Mahsulot: <b>{prod_name}</b>\n"
        f"💰 To'landi: <b>{format_money(price)}</b>\n\n"
        f"🔑 <b>Sizning ma'lumotlaringiz:</b>\n"
        f"<code>{decrypted_data}</code>\n\n"
        f"💳 Qolgan balans: <b>{format_money(db_user.balance)}</b>"
    )

    try:
        await callback.message.edit_caption(caption=text_msg, reply_markup=None)
    except Exception:
        try:
            await callback.message.edit_text(text=text_msg, reply_markup=None)
        except Exception:
            # Telegram yetkazish xatosi (foydalanuvchi bloklagan yoki chat topilmadi)
            await session.execute(text("UPDATE orders SET status = 'DELIVERY_FAILED' WHERE id = :oid"), {"oid": order.id})
            await session.commit()
            
            from core.config import config as _config
            try:
                await callback.bot.send_message(_config.ADMIN_ID, f"⚠️ <b>YETKAZISH XATOSI</b>\nBuyurtma: <code>{order_num}</code>\nXaridorga ma'lumot yetib bormadi (bloklagan bo'lishi mumkin).")
            except Exception:
                pass
                
    try:
        await callback.answer("✅ Ma'lumot yetkazildi!")
    except Exception:
        pass

    # Admin ga xabar yuborish
    from aiogram import Bot
    from core.config import config as _config
    bot: Bot = callback.bot
    buyer = f"@{db_user.username}" if db_user.username else f"ID: {db_user.telegram_id}"
    admin_text = (
        f"🛒 <b>YANGI XARID</b>\n\n"
        f"🧾 Buyurtma: <code>{order_num}</code>\n"
        f"🎮 Mahsulot: <b>{prod_name}</b>\n"
        f"👤 Xaridor: {buyer}\n"
        f"💰 Summa: {format_money(price)}\n\n"
        f"❗️ Iltimos, xaridorga mahsulot yuboring!"
    )
    try:
        await bot.send_message(_config.ADMIN_ID, admin_text)
    except Exception:
        pass


@router.callback_query(F.data == "shop_noop")
async def shop_noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "shop_back_main")
async def back_to_main(callback: CallbackQuery):
    from bot.handlers.registration import get_main_menu_keyboard
    from core.config import config
    is_admin = callback.from_user.id == config.ADMIN_ID

    text = (
        "👋 <b>Asosiy menyu</b>\n\n"
        "<blockquote>Bu PUBG Mobile va o'yin akkauntlari do'koni boti! Kerakli bo'limni tanlang va qulay xarid qiling.</blockquote>"
    )
    try:
        await callback.message.edit_caption(caption=text, reply_markup=get_main_menu_keyboard(lambda x: x, is_admin=is_admin))
    except Exception:
        await callback.message.edit_text(text=text, reply_markup=get_main_menu_keyboard(lambda x: x, is_admin=is_admin))
    await callback.answer()
