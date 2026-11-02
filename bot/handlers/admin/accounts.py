from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.filters.admin import IsAdmin
from bot.states.admin import AddProduct, AddCategory
from db.models.product import Category, Product

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ───────────────────────────────────────────
# KATEGORIYALAR boshqaruvi
# ───────────────────────────────────────────

@router.message(F.text == "📂 Kategoriyalar")
async def manage_categories(message: Message, session: AsyncSession):
    result = await session.execute(
        select(Category).order_by(Category.order_index)
    )
    categories = result.scalars().all()

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Kategoriya qo'shish", callback_data="admin_cat_add")
    for cat in categories:
        status = "✅" if cat.is_active else "❌"
        emoji = f"{cat.emoji} " if cat.emoji else "📁 "
        builder.button(
            text=f"{status} {emoji}{cat.name}",
            callback_data=f"admin_cat_toggle_{cat.id}"
        )
    builder.adjust(1)

    text = f"📂 <b>Kategoriyalar</b> (jami: {len(categories)})\n\nBoshqaruv:"
    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "admin_cat_add")
async def start_add_category(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📂 <b>Yangi kategoriya nomini kiriting:</b>\n\n<i>Masalan: PUBG Mobile 0.80</i>")
    await state.set_state(AddCategory.waiting_for_name)
    await callback.answer()


@router.message(AddCategory.waiting_for_name, F.text)
async def process_category_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await message.answer(
        f"✅ <b>Kategoriya nomi:</b> {name}\n\n"
        f"🌟 <b>Endi bu kategoriya uchun emoji yuboring:</b>\n"
        f"<i>Bunga standart emoji (🎮) yoki premium emoji kiritishingiz mumkin.\n"
        f"O'tkazib yuborish uchun \"/skip\" ni bosing.</i>"
    )
    await state.set_state("waiting_for_category_emoji")


@router.message(F.state == "waiting_for_category_emoji")
async def process_category_emoji(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    name = data.get("name")

    emoji_str = None
    if message.text != "/skip":
        # Premium emoji bo'lsa `message.entities` ichida custom_emoji_id kelishi mumkin.
        # Bu yerda oddiy qilib textni (emojini o'zini) olamiz. (Telegram API orqali HTML formatda ko'rsatish mumkin)
        emoji_str = message.text.strip()

    cat = Category(name=name, emoji=emoji_str, order_index=0, is_active=True)
    session.add(cat)
    await session.commit()
    await state.clear()

    emoji_disp = f"{emoji_str} " if emoji_str else ""
    await message.answer(f"✅ Kategoriya qo'shildi: <b>{emoji_disp}{name}</b> (ID: #{cat.id})")


@router.callback_query(F.data.startswith("admin_cat_toggle_"))
async def toggle_category(callback: CallbackQuery, session: AsyncSession):
    cat_id = int(callback.data.split("_")[3])
    cat = await session.get(Category, cat_id)
    if cat:
        cat.is_active = not cat.is_active
        await session.commit()
        status = "faollashtirildi ✅" if cat.is_active else "o'chirildi ❌"
        await callback.answer(f"Kategoriya {status}")

    await manage_categories_refresh(callback, session)


async def manage_categories_refresh(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(select(Category).order_by(Category.order_index))
    categories = result.scalars().all()

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Kategoriya qo'shish", callback_data="admin_cat_add")
    for c in categories:
        s = "✅" if c.is_active else "❌"
        e = f"{c.emoji} " if c.emoji else "📁 "
        builder.button(text=f"{s} {e}{c.name}",
                       callback_data=f"admin_cat_toggle_{c.id}")
    builder.adjust(1)

    try:
        await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    except Exception:
        pass


# ───────────────────────────────────────────
# MAHSULOTLAR boshqaruvi
# ───────────────────────────────────────────

@router.message(F.text == "🛍 Mahsulotlar")
async def manage_products(message: Message, session: AsyncSession):
    cats_result = await session.execute(
        select(Category).where(Category.is_active ==
                               True).order_by(Category.order_index)
    )
    categories = cats_result.scalars().all()

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Mahsulot qo'shish", callback_data="admin_prod_add")
    for cat in categories:
        e = f"{cat.emoji} " if cat.emoji else "📁 "
        builder.button(text=f"{e}{cat.name}",
                       callback_data=f"admin_prod_list_{cat.id}")
    builder.adjust(1)

    await message.answer("🛍 <b>Mahsulotlar boshqaruvi</b>", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("admin_prod_list_"))
async def list_products_in_category(callback: CallbackQuery, session: AsyncSession):
    cat_id = int(callback.data.split("_")[3])
    cat = await session.get(Category, cat_id)

    result = await session.execute(
        select(Product).where(Product.category_id ==
                              cat_id).order_by(Product.price_uzs)
    )
    products = result.scalars().all()

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Mahsulot qo'shish", callback_data="admin_prod_add")
    for p in products:
        s = "✅" if p.is_active else "❌"
        qty = f"[{p.quantity}]"
        builder.button(
            text=f"{s} {p.name} {qty} — {float(p.price_uzs):,.0f} so'm",
            callback_data=f"admin_prod_detail_{p.id}"
        )
    builder.button(text="↩️ Orqaga", callback_data="admin_prod_back")
    builder.adjust(1)

    e = f"{cat.emoji} " if cat and cat.emoji else "📁 "
    name = cat.name if cat else "Kategoriya"
    text = f"🛍 <b>{e}{name}</b> mahsulotlari ({len(products)} ta):"
    try:
        await callback.message.edit_text(text=text, reply_markup=builder.as_markup())
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prod_detail_"))
async def product_detail_admin(callback: CallbackQuery, session: AsyncSession):
    prod_id = int(callback.data.split("_")[3])
    prod = await session.get(Product, prod_id)
    if not prod:
        await callback.answer("Mahsulot topilmadi!")
        return

    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"{'❌ O\'chirish' if prod.is_active else '✅ Faollashtirish'}",
        callback_data=f"admin_prod_toggle_{prod_id}"
    )
    builder.button(text="📦 Stok qo'shish",
                   callback_data=f"admin_prod_stock_{prod_id}")
    builder.button(text="↩️ Orqaga",
                   callback_data=f"admin_prod_list_{prod.category_id}")
    builder.adjust(1)

    price_usd = f"${prod.price_usd:.2f}" if prod.price_usd else "—"
    text = (
        f"🛍 <b>{prod.name}</b>\n\n"
        f"💰 Narxi: {float(prod.price_uzs):,.0f} so'm ({price_usd})\n"
        f"📦 Stok: {prod.quantity} dona\n"
        f"📝 Tavsif: {prod.description or '—'}\n"
        f"🔘 Holati: {'Faol ✅' if prod.is_active else 'O\'chirilgan ❌'}"
    )
    try:
        await callback.message.edit_text(text=text, reply_markup=builder.as_markup())
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("admin_prod_toggle_"))
async def toggle_product(callback: CallbackQuery, session: AsyncSession):
    prod_id = int(callback.data.split("_")[3])
    prod = await session.get(Product, prod_id)
    if prod:
        prod.is_active = not prod.is_active
        await session.commit()
        status = "faollashtirildi ✅" if prod.is_active else "o'chirildi ❌"
        await callback.answer(f"Mahsulot {status}")
        # Yangilash
        await product_detail_admin(callback, session)


@router.callback_query(F.data.startswith("admin_prod_stock_"))
async def ask_stock(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split("_")[3])
    await state.update_data(prod_id=prod_id)
    await callback.message.edit_text(
        f"📦 <b>Stok qo'shish</b>\n\nMahsulot ID: #{prod_id}\n\nQo'shmoqchi bo'lgan miqdorni kiriting:"
    )
    await state.set_state(AddProduct.waiting_for_stock)
    await callback.answer()


@router.message(AddProduct.waiting_for_stock, F.text)
async def process_stock(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text.lstrip("-").isdigit():
        await message.answer("❌ Raqam kiriting!")
        return

    data = await state.get_data()
    prod_id = data.get("prod_id")
    amount = int(message.text)

    prod = await session.get(Product, prod_id)
    if prod:
        prod.quantity = max(0, prod.quantity + amount)
        await session.commit()
        await message.answer(f"✅ Stok yangilandi! <b>{prod.name}</b>: {prod.quantity} dona")
    await state.clear()


@router.callback_query(F.data == "admin_prod_add")
async def start_add_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    cats_result = await session.execute(
        select(Category).where(Category.is_active ==
                               True).order_by(Category.order_index)
    )
    categories = cats_result.scalars().all()

    builder = InlineKeyboardBuilder()
    for cat in categories:
        e = f"{cat.emoji} " if cat.emoji else "📁 "
        builder.button(text=f"{e}{cat.name}",
                       callback_data=f"admin_prod_setcat_{cat.id}")
    builder.adjust(1)

    await callback.message.edit_text(
        "🛍 <b>Yangi mahsulot qo'shish</b>\n\nAvval kategoriyani tanlang:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(AddProduct.waiting_for_category)
    await callback.answer()


@router.callback_query(AddProduct.waiting_for_category, F.data.startswith("admin_prod_setcat_"))
async def product_category_selected(callback: CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[3])
    await state.update_data(category_id=cat_id)
    await callback.message.edit_text("📝 <b>Mahsulot nomini kiriting:</b>\n\n<i>Masalan: 60 UC</i>")
    await state.set_state(AddProduct.waiting_for_name)
    await callback.answer()


@router.message(AddProduct.waiting_for_name, F.text)
async def product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer(
        "💰 <b>Narxni kiriting (UZS):</b>\n\n<i>Masalan: 38000</i>"
    )
    await state.set_state(AddProduct.waiting_for_price_uzs)


@router.message(AddProduct.waiting_for_price_uzs, F.text)
async def product_price_uzs(message: Message, state: FSMContext):
    if not message.text.replace(".", "").isdigit():
        await message.answer("❌ Raqam kiriting! Masalan: 38000")
        return
    await state.update_data(price_uzs=float(message.text))
    await message.answer("💵 <b>USD narxini kiriting:</b>\n\n<i>Masalan: 3.17 (yo'q bo'lsa 0 kiriting)</i>")
    await state.set_state(AddProduct.waiting_for_price_usd)


@router.message(AddProduct.waiting_for_price_usd, F.text)
async def product_price_usd(message: Message, state: FSMContext):
    try:
        usd = float(message.text)
    except ValueError:
        await message.answer("❌ Raqam kiriting! Masalan: 3.17")
        return
    await state.update_data(price_usd=usd if usd > 0 else None)
    await message.answer("📦 <b>Boshlang'ich stok miqdori:</b>\n\n<i>Masalan: 10</i>")
    await state.set_state(AddProduct.waiting_for_quantity)


@router.message(AddProduct.waiting_for_quantity, F.text)
async def product_quantity(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Butun son kiriting! Masalan: 10")
        return
    await state.update_data(quantity=int(message.text))
    await message.answer("📝 <b>Tavsif kiriting:</b>\n\n<i>Masalan: Avtomatik yetkazib berish.</i>")
    await state.set_state(AddProduct.waiting_for_description)


@router.message(AddProduct.waiting_for_description, F.text)
async def product_description(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    prod = Product(
        category_id=data["category_id"],
        name=data["name"],
        price_uzs=data["price_uzs"],
        price_usd=data.get("price_usd"),
        quantity=data["quantity"],
        description=message.text.strip(),
        is_active=True,
    )
    session.add(prod)
    await session.commit()
    await state.clear()

    price_usd = f"${data.get('price_usd', 0):.2f}" if data.get(
        "price_usd") else "—"
    await message.answer(
        f"✅ <b>Mahsulot qo'shildi!</b>\n\n"
        f"🛍 {prod.name}\n"
        f"💰 {float(prod.price_uzs):,.0f} so'm ({price_usd})\n"
        f"📦 Stok: {prod.quantity} dona\n"
        f"🔑 ID: #{prod.id}"
    )


@router.callback_query(F.data == "admin_prod_back")
async def products_back(callback: CallbackQuery, session: AsyncSession):
    cats_result = await session.execute(
        select(Category).where(Category.is_active ==
                               True).order_by(Category.order_index)
    )
    categories = cats_result.scalars().all()

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Mahsulot qo'shish", callback_data="admin_prod_add")
    for cat in categories:
        e = f"{cat.emoji} " if cat.emoji else "📁 "
        builder.button(text=f"{e}{cat.name}",
                       callback_data=f"admin_prod_list_{cat.id}")
    builder.adjust(1)

    await callback.message.edit_text("🛍 <b>Mahsulotlar boshqaruvi</b>", reply_markup=builder.as_markup())
    await callback.answer()
