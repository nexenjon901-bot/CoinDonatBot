"""Admin: mahsulotlarni boshqarish (UC va akkaunt turlari, tahrirlash, ombor, premium emoji)."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, delete as sa_delete
from bot.filters.admin import IsAdmin
from db.models.product import Product, Category
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from core.security import encrypt_text, decrypt_text
from core.emojis import create_button

UC_STOCK = 9999  # UC uchun ombor cheksiz (Player ID orqali qo'lda yetkaziladi)


class ManageStock(StatesGroup):
    waiting_for_data = State()


class ProductStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_type = State()
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_desc = State()
    waiting_for_image = State()
    editing_name = State()
    editing_price = State()
    editing_desc = State()
    editing_image = State()


router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def _is_uc(p: Product) -> bool:
    return getattr(p, "product_type", "account") == "uc"


def _parse_price(raw: str):
    cleaned = (raw or "").replace(" ", "").replace(",", "").replace("\u00a0", "")
    try:
        v = float(cleaned)
    except ValueError:
        return None
    return v if v > 0 else None


def _cancel_kb():
    b = InlineKeyboardBuilder()
    b.add(create_button("Bekor qilish", emoji_key="cancel", callback_data="adm_prod_cancel"))
    return b.as_markup()


def _skip_kb():
    b = InlineKeyboardBuilder()
    b.add(create_button("O'tkazib yuborish ⏭", callback_data="adm_prod_skip"))
    b.add(create_button("Bekor qilish", emoji_key="cancel", callback_data="adm_prod_cancel"))
    b.adjust(1)
    return b.as_markup()


async def _list_view(session: AsyncSession):
    res = await session.execute(select(Product).order_by(Product.category_id, Product.id))
    products = res.scalars().all()
    builder = InlineKeyboardBuilder()
    builder.add(create_button("Yangi mahsulot", emoji_key="add", callback_data="adm_prod_add"))
    for p in products:
        qty = "∞" if _is_uc(p) else f"{p.quantity} ta"
        mark = "" if p.is_active else " (o'chiq)"
        builder.add(create_button(
            f"{p.name} — {qty}{mark}", emoji_key="uc" if _is_uc(p) else "pubg",
            callback_data=f"adm_prod_{p.id}"))
    builder.adjust(1)
    body = ("<blockquote>💎 UC — Player ID orqali qo'lda yetkaziladi (ombor kerak emas).\n"
            "🎮 Akkaunt — omborga <code>login:parol</code> qo'shiladi, avtomatik beriladi.</blockquote>"
            if products else
            "<blockquote>Hozircha mahsulot yo'q. Avval kategoriya yarating, so'ng «Yangi mahsulot» ni bosing.</blockquote>")
    return f"📦 <b>Mahsulotlar</b> — {len(products)} ta\n\n{body}", builder.as_markup()


async def _detail_view(session: AsyncSession, p: Product):
    cat = await session.get(Category, p.category_id)
    uc = _is_uc(p)
    desc = (p.description or "").strip() or "—"
    text_ = (
        f"{'💎' if uc else '🎮'} <b>{p.name}</b>\n\n"
        f"<blockquote>"
        f"Turi: {'PUBG Mobile UC' if uc else 'O`yin akkaunti'}\n"
        f"Kategoriya: {cat.name if cat else '—'}\n"
        f"Narxi: {float(p.price_uzs):,.0f} so'm\n"
        f"Qoldiq: {'cheksiz (Player ID)' if uc else str(p.quantity) + ' ta'}\n"
        f"Holati: {'🟢 Faol' if p.is_active else '🔴 O`chiq'}\n"
        f"Rasm: {'bor' if p.image_file_id else 'yo`q'}"
        f"</blockquote>\n"
        f"<blockquote>📝 {desc}</blockquote>"
    )
    b = InlineKeyboardBuilder()
    if not uc:
        b.add(create_button("Ombor qo'shish (Login:Parol)", emoji_key="add", callback_data=f"adm_addstock_{p.id}"))
    b.add(create_button("Nomi", emoji_key="note", callback_data=f"adm_prod_editname_{p.id}"))
    b.add(create_button("Narxi", emoji_key="cash", callback_data=f"adm_prod_editprice_{p.id}"))
    b.add(create_button("Tavsif", emoji_key="note", callback_data=f"adm_prod_editdesc_{p.id}"))
    b.add(create_button("Rasm", emoji_key="folderfile", callback_data=f"adm_prod_editimg_{p.id}"))
    b.add(create_button("Yashirish" if p.is_active else "Faollashtirish", emoji_key="refresh",
                        callback_data=f"adm_prod_toggle_{p.id}"))
    b.add(create_button("O'chirish", emoji_key="delete", callback_data=f"adm_prod_del_{p.id}"))
    b.add(create_button("Orqaga", emoji_key="back", callback_data="adm_prod_back"))
    if uc:
        b.adjust(2, 2, 1, 1, 1)
    else:
        b.adjust(1, 2, 2, 1, 1, 1)
    return text_, b.as_markup()


async def _show_detail_new(target: Message, session: AsyncSession, pid: int):
    p = await session.get(Product, pid)
    if p:
        t, kb = await _detail_view(session, p)
        await target.answer(t, reply_markup=kb)


# ─── Ro'yxat ───────────────────────────────────────────────
@router.message(F.text == "🛍 Mahsulotlar")
async def admin_products_list(message: Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    t, kb = await _list_view(session)
    await message.answer(t, reply_markup=kb)


@router.callback_query(F.data == "adm_prod_back")
async def admin_prod_back(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.clear()
    t, kb = await _list_view(session)
    try:
        await callback.message.edit_text(t, reply_markup=kb)
    except Exception:
        await callback.message.answer(t, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "adm_prod_cancel")
async def cancel_any(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.clear()
    await callback.answer("Bekor qilindi")
    t, kb = await _list_view(session)
    await callback.message.answer(t, reply_markup=kb)


@router.callback_query(F.data.regexp(r"^adm_prod_\d+$"))
async def admin_product_detail(callback: CallbackQuery, session: AsyncSession):
    p = await session.get(Product, int(callback.data.rsplit("_", 1)[1]))
    if not p:
        await callback.answer("Topilmadi", show_alert=True)
        return
    t, kb = await _detail_view(session, p)
    try:
        await callback.message.edit_text(t, reply_markup=kb)
    except Exception:
        await callback.message.answer(t, reply_markup=kb)
    await callback.answer()


# ─── Yangi mahsulot: kategoriya → tur → nom → narx → tavsif → rasm ───
@router.callback_query(F.data == "adm_prod_add")
async def add_prod_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    res = await session.execute(select(Category).order_by(Category.order_index, Category.id))
    categories = res.scalars().all()
    if not categories:
        await callback.answer("Avval kategoriya yarating! (📂 Kategoriyalar)", show_alert=True)
        return
    builder = InlineKeyboardBuilder()
    for cat in categories:
        if cat.emoji_id:
            from aiogram.types import InlineKeyboardButton
            builder.add(InlineKeyboardButton(text=cat.name, callback_data=f"adm_prod_cat_{cat.id}",
                                             icon_custom_emoji_id=str(cat.emoji_id)))
        else:
            builder.add(create_button(cat.name, emoji_key="folder", callback_data=f"adm_prod_cat_{cat.id}"))
    builder.add(create_button("Bekor qilish", emoji_key="cancel", callback_data="adm_prod_cancel"))
    builder.adjust(1)
    await state.set_state(ProductStates.waiting_for_category)
    await callback.message.answer(
        "📦 <b>Yangi mahsulot</b>\n\n<blockquote>Qaysi kategoriyaga qo'shamiz?</blockquote>",
        reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(ProductStates.waiting_for_category, F.data.regexp(r"^adm_prod_cat_\d+$"))
async def add_prod_cat(callback: CallbackQuery, state: FSMContext):
    await state.update_data(cat_id=int(callback.data.rsplit("_", 1)[1]))
    await state.set_state(ProductStates.waiting_for_type)
    b = InlineKeyboardBuilder()
    b.add(create_button("PUBG UC (Player ID orqali)", emoji_key="uc", callback_data="adm_prod_type_uc"))
    b.add(create_button("O'yin akkaunti (Login:Parol)", emoji_key="pubg", callback_data="adm_prod_type_account"))
    b.add(create_button("Bekor qilish", emoji_key="cancel", callback_data="adm_prod_cancel"))
    b.adjust(1)
    await callback.message.answer(
        "🧩 <b>Mahsulot turi</b>\n\n"
        "<blockquote>💎 <b>UC</b> — mijoz PUBG Player ID yuboradi, siz qo'lda UC tashlaysiz. Ombor kerak emas.\n"
        "🎮 <b>Akkaunt</b> — omborga login:parol qo'shasiz, mijozga avtomatik beriladi.</blockquote>",
        reply_markup=b.as_markup())
    await callback.answer()


@router.callback_query(ProductStates.waiting_for_type, F.data.in_({"adm_prod_type_uc", "adm_prod_type_account"}))
async def add_prod_type(callback: CallbackQuery, state: FSMContext):
    await state.update_data(ptype=callback.data.replace("adm_prod_type_", ""))
    await state.set_state(ProductStates.waiting_for_name)
    await callback.message.answer(
        "✏️ <b>Nomi</b>\n\n<blockquote>Mahsulot nomini yuboring.\nMasalan: <code>60 UC</code>, <code>325 UC</code> yoki <code>Conqueror akkaunt</code></blockquote>",
        reply_markup=_cancel_kb())
    await callback.answer()


@router.message(ProductStates.waiting_for_name, F.text)
async def add_prod_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if name == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
    if not name or len(name) > 200:
        await message.answer("Nom 1–200 belgidan iborat bo'lishi kerak.")
        return
    await state.update_data(name=name)
    await state.set_state(ProductStates.waiting_for_price)
    await message.answer(
        "💰 <b>Narxi</b>\n\n<blockquote>So'mda yuboring. Masalan: <code>12000</code> yoki <code>12 000</code></blockquote>",
        reply_markup=_cancel_kb())


@router.message(ProductStates.waiting_for_price, F.text)
async def add_prod_price(message: Message, state: FSMContext):
    if message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
    price = _parse_price(message.text)
    if price is None:
        await message.answer("Iltimos, to'g'ri narx kiriting (faqat raqam, 0 dan katta).")
        return
    await state.update_data(price=price)
    await state.set_state(ProductStates.waiting_for_desc)
    await message.answer(
        "📝 <b>Tavsif</b>\n\n<blockquote>Qisqa tavsif yuboring yoki o'tkazib yuboring.</blockquote>",
        reply_markup=_skip_kb())


async def _ask_image(target: Message, state: FSMContext):
    await state.set_state(ProductStates.waiting_for_image)
    await target.answer(
        "🖼 <b>Rasm</b>\n\n<blockquote>Mahsulot rasmini yuboring yoki o'tkazib yuboring.</blockquote>",
        reply_markup=_skip_kb())


@router.message(ProductStates.waiting_for_desc, F.text)
async def add_prod_desc(message: Message, state: FSMContext):
    if message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
    await state.update_data(desc=message.text.strip())
    await _ask_image(message, state)


@router.callback_query(ProductStates.waiting_for_desc, F.data == "adm_prod_skip")
async def skip_desc(callback: CallbackQuery, state: FSMContext):
    await state.update_data(desc=None)
    await _ask_image(callback.message, state)
    await callback.answer()


async def _create_product(target: Message, state: FSMContext, session: AsyncSession, image_id=None):
    data = await state.get_data()
    uc = data.get("ptype") == "uc"
    p = Product(
        category_id=data["cat_id"], name=data["name"], price_uzs=data["price"],
        description=data.get("desc"), image_file_id=image_id,
        product_type="uc" if uc else "account",
        quantity=UC_STOCK if uc else 0, is_active=True,
    )
    session.add(p)
    await session.commit()
    await session.refresh(p)
    await state.clear()
    await target.answer(f"✅ Mahsulot yaratildi: <b>{p.name}</b>")
    await _show_detail_new(target, session, p.id)
    if not uc:
        await target.answer("<blockquote>Akkaunt mahsuloti omborsiz sotilmaydi — yuqoridagi «Ombor qo'shish» tugmasi orqali login:parol qo'shing.</blockquote>")


@router.callback_query(ProductStates.waiting_for_image, F.data == "adm_prod_skip")
async def skip_image(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await _create_product(callback.message, state, session)
    await callback.answer()


@router.message(ProductStates.waiting_for_image)
async def add_prod_image(message: Message, state: FSMContext, session: AsyncSession):
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
    if not message.photo:
        await message.answer("Rasm (photo) yuboring yoki «O'tkazib yuborish» ni bosing.")
        return
    await _create_product(message, state, session, message.photo[-1].file_id)


# ─── Tahrirlash ────────────────────────────────────────────
async def _edit_start(callback: CallbackQuery, state: FSMContext, st, prompt: str):
    await state.set_state(st)
    await state.update_data(prod_id=int(callback.data.rsplit("_", 1)[1]))
    await callback.message.answer(prompt, reply_markup=_cancel_kb())
    await callback.answer()


@router.callback_query(F.data.regexp(r"^adm_prod_editname_\d+$"))
async def edit_name_start(callback: CallbackQuery, state: FSMContext):
    await _edit_start(callback, state, ProductStates.editing_name, "✏️ Yangi nomni yuboring:")


@router.callback_query(F.data.regexp(r"^adm_prod_editprice_\d+$"))
async def edit_price_start(callback: CallbackQuery, state: FSMContext):
    await _edit_start(callback, state, ProductStates.editing_price, "💰 Yangi narxni yuboring (so'mda):")


@router.callback_query(F.data.regexp(r"^adm_prod_editdesc_\d+$"))
async def edit_desc_start(callback: CallbackQuery, state: FSMContext):
    await _edit_start(callback, state, ProductStates.editing_desc, "📝 Yangi tavsifni yuboring (tozalash uchun: <code>-</code>):")


@router.callback_query(F.data.regexp(r"^adm_prod_editimg_\d+$"))
async def edit_img_start(callback: CallbackQuery, state: FSMContext):
    await _edit_start(callback, state, ProductStates.editing_image, "🖼 Yangi rasmni yuboring:")


async def _finish_edit(message: Message, state: FSMContext, session: AsyncSession, field: str, value):
    data = await state.get_data()
    p = await session.get(Product, data["prod_id"])
    if not p:
        await state.clear()
        await message.answer("Mahsulot topilmadi.")
        return
    setattr(p, field, value)
    if field == "price_uzs":
        p.price_usd = None  # do'konda kurs bo'yicha qayta hisoblanadi
    await session.commit()
    await state.clear()
    await message.answer("✅ Yangilandi.")
    await _show_detail_new(message, session, p.id)


@router.message(ProductStates.editing_name, F.text)
async def edit_name_done(message: Message, state: FSMContext, session: AsyncSession):
    name = message.text.strip()
    if not name or len(name) > 200:
        await message.answer("Nom 1–200 belgidan iborat bo'lishi kerak.")
        return
    await _finish_edit(message, state, session, "name", name)


@router.message(ProductStates.editing_price, F.text)
async def edit_price_done(message: Message, state: FSMContext, session: AsyncSession):
    price = _parse_price(message.text)
    if price is None:
        await message.answer("Iltimos, to'g'ri narx kiriting.")
        return
    await _finish_edit(message, state, session, "price_uzs", price)


@router.message(ProductStates.editing_desc, F.text)
async def edit_desc_done(message: Message, state: FSMContext, session: AsyncSession):
    v = message.text.strip()
    await _finish_edit(message, state, session, "description", None if v == "-" else v)


@router.message(ProductStates.editing_image, F.photo)
async def edit_img_done(message: Message, state: FSMContext, session: AsyncSession):
    await _finish_edit(message, state, session, "image_file_id", message.photo[-1].file_id)


@router.callback_query(F.data.regexp(r"^adm_prod_toggle_\d+$"))
async def toggle_product(callback: CallbackQuery, session: AsyncSession):
    p = await session.get(Product, int(callback.data.rsplit("_", 1)[1]))
    if not p:
        await callback.answer("Topilmadi", show_alert=True)
        return
    p.is_active = not p.is_active
    await session.commit()
    await callback.answer("🟢 Faollashtirildi" if p.is_active else "🔴 Do'kondan yashirildi")
    t, kb = await _detail_view(session, p)
    try:
        await callback.message.edit_text(t, reply_markup=kb)
    except Exception:
        pass


# ─── Ombor (faqat akkauntlar uchun) ────────────────────────
@router.callback_query(F.data.regexp(r"^adm_addstock_\d+$"))
async def add_stock_start(callback: CallbackQuery, state: FSMContext):
    pid = int(callback.data.split("_")[2])
    await state.update_data(product_id=pid)
    await state.set_state(ManageStock.waiting_for_data)
    
    await callback.message.answer(
        "📝 <b>Ombor qo'shish</b>\n\n"
        "<blockquote>Akkaunt ma'lumotlarini yuboring — <b>har qatorda bittadan</b> "
        "(masalan: <code>login:parol</code>).\n"
        "Yoki <code>.txt</code> fayl yuklang.</blockquote>\n\n"
        "Bekor qilish: /cancel"
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

@router.callback_query(F.data.regexp(r"^adm_prod_del_\d+$"))
async def delete_ask(callback: CallbackQuery, session: AsyncSession):
    pid = int(callback.data.rsplit("_", 1)[1])
    p = await session.get(Product, pid)
    if not p:
        await callback.answer("Topilmadi", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    b.add(create_button("Ha, o'chirish", emoji_key="delete", callback_data=f"adm_prod_delok_{pid}"))
    b.add(create_button("Yo'q", emoji_key="cancel", callback_data=f"adm_prod_{pid}"))
    b.adjust(1)
    try:
        await callback.message.edit_text(
            f"🗑 <b>{p.name}</b> o'chirilsinmi?\n\n<blockquote>Ombordagi barcha ma'lumotlar ham o'chadi. "
            f"Buyurtma tarixi bor bo'lsa, mahsulot o'chirilmasdan do'kondan yashiriladi.</blockquote>",
            reply_markup=b.as_markup())
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.regexp(r"^adm_prod_delok_\d+$"))
async def delete_product(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    pid = int(callback.data.rsplit("_", 1)[1])
    try:
        await session.execute(sa_delete(Product).where(Product.id == pid))
        await session.commit()
        await callback.answer("Mahsulot o'chirildi!", show_alert=True)
    except Exception:
        await session.rollback()
        p = await session.get(Product, pid)
        if p:
            p.is_active = False
            await session.commit()
        await callback.answer(
            "Buyurtmalar bog'langani uchun o'chirib bo'lmadi — mahsulot do'kondan yashirildi.",
            show_alert=True)
    await admin_prod_back(callback, session, state)
