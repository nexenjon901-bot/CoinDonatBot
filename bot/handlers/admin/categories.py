from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.filters.admin import IsAdmin
from db.models.product import Category

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

class CategoryStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_image = State()

@router.message(F.text == "📂 Kategoriyalar")
async def list_categories(message: Message, session: AsyncSession):
    res = await session.execute(select(Category).order_by(Category.order_index))
    categories = res.scalars().all()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yangi kategoriya", callback_data="adm_cat_add")
    for cat in categories:
        builder.button(text=f"{cat.name}", callback_data=f"adm_cat_view_{cat.id}")
    builder.adjust(1)
    
    await message.answer("📂 <b>Kategoriyalar</b>\n\nBoshqarish uchun tanlang:", reply_markup=builder.as_markup())

@router.callback_query(F.data == "adm_cat_add")
async def add_cat_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CategoryStates.waiting_for_name)
    await callback.message.answer("Yangi kategoriya nomini kiriting:\nBekor qilish uchun /cancel")
    await callback.answer()

@router.message(CategoryStates.waiting_for_name)
async def add_cat_name(message: Message, state: FSMContext, session: AsyncSession):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
        
    new_cat = Category(name=message.text, is_active=True)
    session.add(new_cat)
    await session.commit()
    await session.refresh(new_cat)
    
    await state.update_data(cat_id=new_cat.id)
    await state.set_state(CategoryStates.waiting_for_image)
    await message.answer(f"✅ Kategoriya yaratildi: {new_cat.name}\nEndi shu kategoriya uchun rasm (photo) yuboring. Yoki o'tkazib yuborish uchun /skip bosing.")

@router.message(CategoryStates.waiting_for_image, F.photo | F.text)
async def add_cat_image(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    cat_id = data.get("cat_id")
    
    cat = await session.get(Category, cat_id)
    
    if message.text == "/skip":
        await state.clear()
        await message.answer("Rasm o'tkazib yuborildi.")
        return
        
    if message.photo:
        file_id = message.photo[-1].file_id
        cat.image_file_id = file_id
        await session.commit()
        await state.clear()
        await message.answer("✅ Rasm saqlandi!")
    else:
        await message.answer("Rasm yuboring yoki /skip bosing.")

@router.callback_query(F.data.startswith("adm_cat_view_"))
async def view_category(callback: CallbackQuery, session: AsyncSession):
    cat_id = int(callback.data.split("_")[3])
    cat = await session.get(Category, cat_id)
    
    if not cat:
        await callback.answer("Topilmadi", show_alert=True)
        return
        
    txt = f"📂 <b>{cat.name}</b>\nFaol: {'Ha' if cat.is_active else 'Yoq'}\n"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 O'chirish", callback_data=f"adm_cat_del_{cat_id}")
    builder.button(text="🔙 Orqaga", callback_data="adm_cat_back")
    
    try:
        await callback.message.edit_text(txt, reply_markup=builder.as_markup())
    except Exception:
        pass

@router.callback_query(F.data == "adm_cat_back")
async def back_to_cats(callback: CallbackQuery, session: AsyncSession):
    res = await session.execute(select(Category).order_by(Category.order_index))
    categories = res.scalars().all()
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yangi kategoriya", callback_data="adm_cat_add")
    for cat in categories:
        builder.button(text=f"{cat.name}", callback_data=f"adm_cat_view_{cat.id}")
    builder.adjust(1)
    try:
        await callback.message.edit_text("📂 <b>Kategoriyalar</b>\n\nBoshqarish uchun tanlang:", reply_markup=builder.as_markup())
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("adm_cat_del_"))
async def delete_category(callback: CallbackQuery, session: AsyncSession):
    cat_id = int(callback.data.split("_")[3])
    await session.execute(text("DELETE FROM categories WHERE id = :id"), {"id": cat_id})
    await session.commit()
    await callback.answer("Kategoriya o'chirildi!", show_alert=True)
    await back_to_cats(callback, session)
