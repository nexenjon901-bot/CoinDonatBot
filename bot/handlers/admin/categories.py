"""Admin: kategoriyalarni boshqarish (qo'shish, tahrirlash, premium emoji, faollik, o'chirish)."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete as sa_delete

from bot.filters.admin import IsAdmin
from core.emojis import create_button, extract_custom_emoji_id
from db.models.product import Category, Product
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class CategoryStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_emoji = State()
    waiting_for_image = State()
    editing_name = State()
    editing_emoji = State()
    editing_image = State()


def _cancel_kb():
    b = InlineKeyboardBuilder()
    b.add(create_button("Bekor qilish", emoji_key="cancel", callback_data="adm_cat_cancel"))
    return b.as_markup()


def _skip_kb(back_cb: str = "adm_cat_cancel"):
    b = InlineKeyboardBuilder()
    b.add(create_button("O'tkazib yuborish ⏭", callback_data="adm_cat_skip"))
    b.add(create_button("Bekor qilish", emoji_key="cancel", callback_data=back_cb))
    b.adjust(1)
    return b.as_markup()


async def _list_view(session: AsyncSession):
    res = await session.execute(select(Category).order_by(Category.order_index, Category.id))
    categories = res.scalars().all()
    counts = dict((await session.execute(
        select(Product.category_id, func.count(Product.id)).group_by(Product.category_id)
    )).all())

    builder = InlineKeyboardBuilder()
    builder.add(create_button("Yangi kategoriya", emoji_key="add", callback_data="adm_cat_add"))
    for cat in categories:
        mark = "" if cat.is_active else " (o'chiq)"
        builder.add(create_button(
            f"{cat.name} — {counts.get(cat.id, 0)} ta{mark}",
            emoji_key="folder", callback_data=f"adm_cat_view_{cat.id}",
        ))
    builder.adjust(1)
    body = (
        "<blockquote>Kategoriya — do'kondagi bo'lim (masalan: <b>PUBG UC</b>, <b>PUBG Akkauntlar</b>). "
        "Mahsulotlar kategoriya ichiga qo'shiladi.</blockquote>"
        if categories else
        "<blockquote>Hozircha kategoriya yo'q. «Yangi kategoriya» tugmasi orqali qo'shing.</blockquote>"
    )
    return f"📂 <b>Kategoriyalar</b> — {len(categories)} ta\n\n{body}", builder.as_markup()


async def _detail_view(session: AsyncSession, cat: Category):
    cnt = (await session.execute(
        select(func.count(Product.id)).where(Product.category_id == cat.id)
    )).scalar() or 0
    emoji_info = "✨ Premium emoji" if cat.emoji_id else (cat.emoji or "—")
    text = (
        f"📂 <b>{cat.name}</b>\n\n"
        f"<blockquote>"
        f"Holati: {'🟢 Faol' if cat.is_active else '🔴 O`chiq'}\n"
        f"Emoji: {emoji_info}\n"
        f"Rasm: {'bor' if cat.image_file_id else 'yo`q'}\n"
        f"Mahsulotlar: {cnt} ta"
        f"</blockquote>"
    )
    b = InlineKeyboardBuilder()
    b.add(create_button("Nomini o'zgartirish", emoji_key="note", callback_data=f"adm_cat_rename_{cat.id}"))
    b.add(create_button("Emoji o'rnatish", emoji_key="star", callback_data=f"adm_cat_emoji_{cat.id}"))
    b.add(create_button("Rasm o'zgartirish", emoji_key="folderfile", callback_data=f"adm_cat_img_{cat.id}"))
    b.add(create_button("O'chirish" if cat.is_active else "Yoqish", emoji_key="refresh",
                        callback_data=f"adm_cat_toggle_{cat.id}"))
    b.add(create_button("Kategoriyani o'chirish", emoji_key="delete", callback_data=f"adm_cat_del_{cat.id}"))
    b.add(create_button("Orqaga", emoji_key="back", callback_data="adm_cat_back"))
    b.adjust(1, 2, 1, 1, 1)
    return text, b.as_markup()


async def _show_detail(target: Message, session: AsyncSession, cat_id: int):
    cat = await session.get(Category, cat_id)
    if not cat:
        await target.answer("Kategoriya topilmadi.")
        return
    text, kb = await _detail_view(session, cat)
    await target.answer(text, reply_markup=kb)


def _apply_emoji(cat: Category, msg: Message) -> bool:
    """Xabardan premium yoki oddiy emojini kategoriyaga yozadi."""
    eid, fallback = extract_custom_emoji_id(msg)
    if eid:
        cat.emoji_id = eid
        cat.emoji = fallback
        return True
    raw = (msg.text or "").strip()
    if raw and len(raw) <= 8 and not raw.isalnum():
        cat.emoji = raw
        cat.emoji_id = None
        return True
    return False


# ─── Ro'yxat ───────────────────────────────────────────────
@router.message(F.text == "📂 Kategoriyalar")
async def list_categories(message: Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    text, kb = await _list_view(session)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "adm_cat_back")
async def back_to_cats(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.clear()
    text, kb = await _list_view(session)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "adm_cat_cancel")
async def cancel_any(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.clear()
    await callback.answer("Bekor qilindi")
    text, kb = await _list_view(session)
    await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.regexp(r"^adm_cat_view_\d+$"))
async def view_category(callback: CallbackQuery, session: AsyncSession):
    cat = await session.get(Category, int(callback.data.rsplit("_", 1)[1]))
    if not cat:
        await callback.answer("Topilmadi", show_alert=True)
        return
    text, kb = await _detail_view(session, cat)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


# ─── Yangi kategoriya: nom → emoji → rasm ──────────────────
@router.callback_query(F.data == "adm_cat_add")
async def add_cat_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CategoryStates.waiting_for_name)
    await callback.message.answer(
        "📂 <b>Yangi kategoriya</b>\n\n"
        "<blockquote>Kategoriya nomini yuboring.\n"
        "Masalan: <code>PUBG UC</code> yoki <code>PUBG Akkauntlar</code></blockquote>",
        reply_markup=_cancel_kb(),
    )
    await callback.answer()


@router.message(CategoryStates.waiting_for_name, F.text)
async def add_cat_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if name == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
    if not name or len(name) > 100:
        await message.answer("Nom 1–100 belgidan iborat bo'lishi kerak.")
        return
    await state.update_data(name=name)
    await state.set_state(CategoryStates.waiting_for_emoji)
    await message.answer(
        "✨ <b>Emoji</b>\n\n"
        "<blockquote>Kategoriya tugmasi uchun emoji yuboring. "
        "<b>Telegram Premium emoji</b> ham bo'ladi — shunchaki shu emojini xabarga qo'yib yuboring.</blockquote>",
        reply_markup=_skip_kb(),
    )


@router.message(CategoryStates.waiting_for_emoji, F.text)
async def add_cat_emoji(message: Message, state: FSMContext):
    if message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
    eid, fallback = extract_custom_emoji_id(message)
    raw = message.text.strip()
    if eid:
        await state.update_data(emoji=fallback, emoji_id=eid)
    elif raw and len(raw) <= 8 and not raw.isalnum():
        await state.update_data(emoji=raw, emoji_id=None)
    else:
        await message.answer("Faqat emoji yuboring yoki «O'tkazib yuborish» ni bosing.")
        return
    await _ask_image(message, state)


async def _ask_image(message: Message, state: FSMContext):
    await state.set_state(CategoryStates.waiting_for_image)
    await message.answer(
        "🖼 <b>Rasm</b>\n\n<blockquote>Kategoriya uchun rasm (photo) yuboring yoki o'tkazib yuboring.</blockquote>",
        reply_markup=_skip_kb(),
    )


@router.callback_query(F.data == "adm_cat_skip", CategoryStates.waiting_for_emoji)
async def skip_emoji(callback: CallbackQuery, state: FSMContext):
    await _ask_image(callback.message, state)
    await callback.answer()


async def _finish_create(message: Message, state: FSMContext, session: AsyncSession, image_id=None):
    data = await state.get_data()
    max_idx = (await session.execute(select(func.max(Category.order_index)))).scalar() or 0
    cat = Category(
        name=data["name"], emoji=data.get("emoji"), emoji_id=data.get("emoji_id"),
        image_file_id=image_id, order_index=max_idx + 1, is_active=True,
    )
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    await state.clear()
    await message.answer(f"✅ Kategoriya yaratildi: <b>{cat.name}</b>")
    await _show_detail(message, session, cat.id)


@router.callback_query(F.data == "adm_cat_skip", CategoryStates.waiting_for_image)
async def skip_image(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await _finish_create(callback.message, state, session)
    await callback.answer()


@router.message(CategoryStates.waiting_for_image)
async def add_cat_image(message: Message, state: FSMContext, session: AsyncSession):
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
    if not message.photo:
        await message.answer("Rasm (photo) yuboring yoki «O'tkazib yuborish» ni bosing.")
        return
    await _finish_create(message, state, session, message.photo[-1].file_id)


# ─── Tahrirlash ────────────────────────────────────────────
@router.callback_query(F.data.regexp(r"^adm_cat_rename_\d+$"))
async def rename_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CategoryStates.editing_name)
    await state.update_data(cat_id=int(callback.data.rsplit("_", 1)[1]))
    await callback.message.answer("Yangi nomni yuboring:", reply_markup=_cancel_kb())
    await callback.answer()


@router.message(CategoryStates.editing_name, F.text)
async def rename_done(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    cat = await session.get(Category, data["cat_id"])
    name = message.text.strip()
    if not cat or not name or len(name) > 100:
        await message.answer("Nom 1–100 belgidan iborat bo'lishi kerak.")
        return
    cat.name = name
    await session.commit()
    await state.clear()
    await message.answer("✅ Nom yangilandi.")
    await _show_detail(message, session, cat.id)


@router.callback_query(F.data.regexp(r"^adm_cat_emoji_\d+$"))
async def emoji_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CategoryStates.editing_emoji)
    await state.update_data(cat_id=int(callback.data.rsplit("_", 1)[1]))
    await callback.message.answer(
        "✨ Yangi emojini yuboring (Premium emoji ham bo'ladi).", reply_markup=_cancel_kb())
    await callback.answer()


@router.message(CategoryStates.editing_emoji, F.text)
async def emoji_done(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    cat = await session.get(Category, data["cat_id"])
    if not cat or not _apply_emoji(cat, message):
        await message.answer("Faqat emoji yuboring.")
        return
    await session.commit()
    await state.clear()
    await message.answer("✅ Emoji yangilandi.")
    await _show_detail(message, session, cat.id)


@router.callback_query(F.data.regexp(r"^adm_cat_img_\d+$"))
async def img_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CategoryStates.editing_image)
    await state.update_data(cat_id=int(callback.data.rsplit("_", 1)[1]))
    await callback.message.answer("🖼 Yangi rasmni yuboring:", reply_markup=_cancel_kb())
    await callback.answer()


@router.message(CategoryStates.editing_image, F.photo)
async def img_done(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    cat = await session.get(Category, data["cat_id"])
    if cat:
        cat.image_file_id = message.photo[-1].file_id
        await session.commit()
    await state.clear()
    await message.answer("✅ Rasm yangilandi.")
    if cat:
        await _show_detail(message, session, cat.id)


@router.callback_query(F.data.regexp(r"^adm_cat_toggle_\d+$"))
async def toggle_category(callback: CallbackQuery, session: AsyncSession):
    cat = await session.get(Category, int(callback.data.rsplit("_", 1)[1]))
    if not cat:
        await callback.answer("Topilmadi", show_alert=True)
        return
    cat.is_active = not cat.is_active
    await session.commit()
    await callback.answer("🟢 Faollashtirildi" if cat.is_active else "🔴 Do'kondan yashirildi")
    text, kb = await _detail_view(session, cat)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        pass


# ─── O'chirish (tasdiq bilan) ──────────────────────────────
@router.callback_query(F.data.regexp(r"^adm_cat_del_\d+$"))
async def delete_ask(callback: CallbackQuery, session: AsyncSession):
    cat_id = int(callback.data.rsplit("_", 1)[1])
    cat = await session.get(Category, cat_id)
    if not cat:
        await callback.answer("Topilmadi", show_alert=True)
        return
    cnt = (await session.execute(
        select(func.count(Product.id)).where(Product.category_id == cat_id))).scalar() or 0
    b = InlineKeyboardBuilder()
    b.add(create_button("Ha, o'chirish", emoji_key="delete", callback_data=f"adm_cat_delok_{cat_id}"))
    b.add(create_button("Yo'q", emoji_key="cancel", callback_data=f"adm_cat_view_{cat_id}"))
    b.adjust(1)
    warn = (f"Ichidagi <b>{cnt} ta mahsulot</b> ham o'chadi (buyurtmasi bor mahsulotlar bo'lsa, "
            f"o'chirish o'rniga yashirish tavsiya etiladi).") if cnt else "Ichida mahsulot yo'q."
    try:
        await callback.message.edit_text(
            f"🗑 <b>{cat.name}</b> o'chirilsinmi?\n\n<blockquote>{warn}</blockquote>",
            reply_markup=b.as_markup())
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.regexp(r"^adm_cat_delok_\d+$"))
async def delete_category(callback: CallbackQuery, session: AsyncSession):
    cat_id = int(callback.data.rsplit("_", 1)[1])
    cat = await session.get(Category, cat_id)
    if cat:
        try:
            await session.execute(sa_delete(Category).where(Category.id == cat_id))
            await session.commit()
            await callback.answer("Kategoriya o'chirildi!", show_alert=True)
        except Exception:
            await session.rollback()
            # Buyurtmalar bog'langan — o'chirib bo'lmaydi, faqat yashiramiz
            cat = await session.get(Category, cat_id)
            if cat:
                cat.is_active = False
                await session.commit()
            await callback.answer(
                "Buyurtmalar bog'langani uchun o'chirib bo'lmadi — kategoriya do'kondan yashirildi.",
                show_alert=True)
    else:
        await callback.answer("Topilmadi", show_alert=True)
    text, kb = await _list_view(session)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
