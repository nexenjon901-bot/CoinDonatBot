from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from bot.filters.admin import IsAdmin
from db.models.product import Product
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from core.security import encrypt_text, decrypt_text

class ManageStock(StatesGroup):
    waiting_for_data = State()

class ProductStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_desc = State()
    waiting_for_image = State()

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

@router.message(F.text == "🛍 Mahsulotlar")
async def admin_products_list(message: Message, session: AsyncSession):
    res = await session.execute(select(Product))
    products = res.scalars().all()
    
    if not products:
        await message.answer("Mahsulotlar yo'q. Dastlab bazaga mahsulot qo'shing.")
        return
        
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yangi mahsulot", callback_data="adm_prod_add")
    for p in products:
        icon = "💎" if getattr(p, "product_type", "account") == "uc" else "🎮"
        qty_str = "Cheksiz" if getattr(p, "product_type", "account") == "uc" else f"{p.quantity} ta"
        builder.button(text=f"{icon} {p.name} ({qty_str})", callback_data=f"adm_prod_{p.id}")
    builder.adjust(1)
    await message.answer("📦 <b>Mahsulotlar</b>\n\nMahsulotni tanlang:", reply_markup=builder.as_markup())

@router.callback_query(F.data == "adm_prod_add")
async def add_prod_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    from db.models.product import Category
    res = await session.execute(select(Category).order_by(Category.order_index))
    categories = res.scalars().all()
    if not categories:
        await callback.answer("Avval kategoriya yarating!", show_alert=True)
        return
        
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat.name, callback_data=f"adm_prod_cat_{cat.id}")
    builder.adjust(1)
    
    await state.set_state(ProductStates.waiting_for_category)
    await callback.message.answer("Qaysi kategoriyaga qo'shasiz?", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(ProductStates.waiting_for_category, F.data.startswith("adm_prod_cat_"))
async def add_prod_cat(callback: CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[3])
    await state.update_data(cat_id=cat_id)
    await state.set_state(ProductStates.waiting_for_name)
    await callback.message.answer("Mahsulot nomini kiriting:\nBekor qilish: /cancel")
    await callback.answer()

@router.message(ProductStates.waiting_for_name)
async def add_prod_name(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
    await state.update_data(name=message.text)
    await state.set_state(ProductStates.waiting_for_price)
    await message.answer("Narxini kiriting (UZS, faqat raqam):")

@router.message(ProductStates.waiting_for_price)
async def add_prod_price(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await state.set_state(ProductStates.waiting_for_desc)
        await message.answer("Tavsifni kiriting:")
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting.")

@router.message(ProductStates.waiting_for_desc)
async def add_prod_desc(message: Message, state: FSMContext, session: AsyncSession):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
        
    data = await state.get_data()
    from db.models.product import Category
    cat = await session.get(Category, data['cat_id'])
    is_uc = cat and "UC" in cat.name.upper()

    new_prod = Product(
        category_id=data['cat_id'],
        name=data['name'],
        price_uzs=data['price'],
        description=message.text,
        product_type="uc" if is_uc else "account",
        quantity=9999 if is_uc else 0,
        is_active=True
    )
    session.add(new_prod)
    await session.commit()
    await session.refresh(new_prod)
    
    await state.update_data(prod_id=new_prod.id)
    await state.set_state(ProductStates.waiting_for_image)
    await message.answer(f"✅ Yaratildi: {new_prod.name}\nEndi rasm (photo) yuboring. O'tkazib yuborish: /skip")

@router.message(ProductStates.waiting_for_image, F.photo | F.text)
async def add_prod_image(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    prod_id = data.get("prod_id")
    prod = await session.get(Product, prod_id)
    
    if message.text == "/skip":
        await state.clear()
        await message.answer("Rasm o'tkazib yuborildi.")
        return
        
    if message.photo:
        file_id = message.photo[-1].file_id
        prod.image_file_id = file_id
        await session.commit()
        await state.clear()
        await message.answer("✅ Rasm saqlandi!")
    else:
        await message.answer("Rasm yuboring yoki /skip bosing.")

@router.callback_query(F.data.startswith("adm_prod_"))
async def admin_product_detail(callback: CallbackQuery, session: AsyncSession):
    pid = int(callback.data.split("_")[2])
    p = await session.get(Product, pid)
    if not p:
        await callback.answer("Topilmadi", show_alert=True)
        return
    
    is_uc = getattr(p, "product_type", "account") == "uc"
    icon = "💎" if is_uc else "🎮"
    type_name = "PUBG Mobile UC" if is_uc else "O'yin akkaunti"

    builder = InlineKeyboardBuilder()
    if not is_uc:
        builder.button(text="➕ Ombor qo'shish (Login:Parol)", callback_data=f"adm_addstock_{pid}")
    else:
        builder.button(text="➕ Ombor qo'shish (Redeem Kod)", callback_data=f"adm_addstock_{pid}")
    builder.button(text="🗑 O'chirish", callback_data=f"adm_prod_del_{pid}")
    builder.button(text="Orqaga", callback_data="adm_prod_back")
    builder.adjust(1)
    
    qty_text = "Cheksiz (Player ID)" if is_uc else f"{p.quantity} ta"
    txt = f"{icon} <b>{p.name}</b>\n📁 Turi: {type_name}\n💰 Narxi: {float(p.price_uzs):,.0f} so'm\n📦 Qoldiq: {qty_text}\n📝 Tavsif: {p.description or 'Yoq'}"
    try:
        await callback.message.edit_text(txt, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(txt, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "adm_prod_back")
async def admin_prod_back(callback: CallbackQuery, session: AsyncSession):
    res = await session.execute(select(Product))
    products = res.scalars().all()
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yangi mahsulot", callback_data="adm_prod_add")
    for p in products:
        icon = "💎" if getattr(p, "product_type", "account") == "uc" else "🎮"
        qty_str = "Cheksiz" if getattr(p, "product_type", "account") == "uc" else f"{p.quantity} ta"
        builder.button(text=f"{icon} {p.name} ({qty_str})", callback_data=f"adm_prod_{p.id}")
    builder.adjust(1)
    try:
        await callback.message.edit_text("📦 <b>Mahsulotlar</b>\n\nMahsulotni tanlang:", reply_markup=builder.as_markup())
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("adm_addstock_"))
async def add_stock_start(callback: CallbackQuery, state: FSMContext):
    pid = int(callback.data.split("_")[2])
    await state.update_data(product_id=pid)
    await state.set_state(ManageStock.waiting_for_data)
    
    await callback.message.answer(
        "📝 Yuboriladigan ma'lumotlarni matn ko'rinishida yuboring (har qatorda bittadan).\n"
        "Yoki <code>.txt</code> formatidagi fayl yuklang.\n\n"
        "Bekor qilish uchun /cancel bosing."
    )
    await callback.answer()

@router.message(ManageStock.waiting_for_data)
async def process_add_stock(message: Message, state: FSMContext, session: AsyncSession):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi.")
        return

    data = await state.get_data()
    pid = data.get("product_id")
    
    lines = []
    if message.document:
        if not message.document.file_name.endswith(".txt"):
            await message.answer("Faqat .txt fayl qabul qilinadi!")
            return
        file_id = message.document.file_id
        file = await message.bot.get_file(file_id)
        downloaded = await message.bot.download_file(file.file_path)
        content = downloaded.read().decode('utf-8')
        lines = [line.strip() for line in content.split('\n') if line.strip()]
    elif message.text:
        lines = [line.strip() for line in message.text.split('\n') if line.strip()]
    
    if not lines:
        await message.answer("Ma'lumot topilmadi!")
        return
        
    # Check existing to avoid duplicates
    res = await session.execute(text("SELECT data_encrypted FROM stock_items WHERE product_id = :pid AND status = 'AVAILABLE'"), {"pid": pid})
    existing_stock = res.fetchall()
    
    existing_texts = set()
    for row in existing_stock:
        try:
            existing_texts.add(decrypt_text(row[0]))
        except Exception:
            pass
            
    added = 0
    duplicates = 0
    
    for line in lines:
        if line in existing_texts:
            duplicates += 1
            continue
            
        enc = encrypt_text(line)
        await session.execute(
            text("INSERT INTO stock_items (product_id, data_encrypted, status, created_at) VALUES (:pid, :enc, 'AVAILABLE', NOW())"),
            {"pid": pid, "enc": enc}
        )
        existing_texts.add(line)
        added += 1
        
    if added > 0:
        await session.execute(
            text("UPDATE products SET quantity = quantity + :added WHERE id = :pid"),
            {"added": added, "pid": pid}
        )
        await session.commit()
        
    await message.answer(f"✅ <b>Bajarildi!</b>\n\nQo'shildi: {added} ta\nTakrorlanganlar: {duplicates} ta")
    await state.clear()

@router.callback_query(F.data.startswith("adm_prod_del_"))
async def delete_product(callback: CallbackQuery, session: AsyncSession):
    pid = int(callback.data.split("_")[3])
    await session.execute(text("DELETE FROM products WHERE id = :id"), {"id": pid})
    await session.commit()
    await callback.answer("Mahsulot o'chirildi!", show_alert=True)
    await admin_prod_back(callback, session)
