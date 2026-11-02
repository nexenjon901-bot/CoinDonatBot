from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup

from bot.filters.admin import IsAdmin
from db.models.setting import Setting, SettingKeys

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class AdminSettings(StatesGroup):
    waiting_for_card = State()
    waiting_for_card_owner = State()
    waiting_for_ref_pct = State()
    waiting_for_cb_pct = State()
    waiting_for_min_withdraw = State()


@router.message(F.text == "⚙️ Sozlamalar")
async def show_settings(message: Message, session: AsyncSession):
    async def get_val(key, default):
        res = await session.execute(select(Setting).where(Setting.key == key))
        s = res.scalar_one_or_none()
        return s.value if s else default

    card_val = await get_val(SettingKeys.PAYMENT_CARD, "Kiritilmagan")
    owner_val = await get_val(SettingKeys.PAYMENT_CARD_OWNER, "Kiritilmagan")
    ref_pct = await get_val(SettingKeys.REFERRAL_PERCENT, "2")
    cb_pct = await get_val(SettingKeys.CASHBACK_PERCENT, "1")
    min_wd = await get_val(SettingKeys.MIN_WITHDRAWAL, "10000")

    text = (
        f"⚙️ <b>Bot sozlamalari</b>\n\n"
        f"💳 <b>Karta raqami:</b> <code>{card_val}</code>\n"
        f"👤 <b>Karta egasi:</b> {owner_val}\n\n"
        f"🎁 <b>Referal bonus:</b> {ref_pct}%\n"
        f"💸 <b>Xaridor keshbeki:</b> {cb_pct}%\n"
        f"💰 <b>Minimal yechish:</b> {min_wd} so'm\n\n"
        f"O'zgartirish uchun quyidagi tugmani bosing."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Kartani o'zgartirish", callback_data="admin_set_card")
    builder.button(text="🎁 Referal bonusni o'zgartirish", callback_data="admin_set_ref")
    builder.button(text="💸 Keshbekni o'zgartirish", callback_data="admin_set_cb")
    builder.button(text="💰 Min. yechishni o'zgartirish", callback_data="admin_set_min_wd")
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "admin_set_card")
async def ask_card(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("💳 <b>Yangi karta raqamini kiriting:</b>\n\n<i>Masalan: 8600 1234 5678 9012</i>")
    await state.set_state(AdminSettings.waiting_for_card)
    await callback.answer()


@router.message(AdminSettings.waiting_for_card, F.text)
async def process_card(message: Message, state: FSMContext):
    await state.update_data(card=message.text.strip())
    await message.answer("👤 <b>Karta egasining ismini kiriting:</b>\n\n<i>Masalan: Olimov O.</i>")
    await state.set_state(AdminSettings.waiting_for_card_owner)


@router.message(AdminSettings.waiting_for_card_owner, F.text)
async def process_card_owner(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    card = data.get("card")
    owner = message.text.strip()

    # Bazada yangilash yoki yaratish
    async def _update_setting(key, value):
        res = await session.execute(select(Setting).where(Setting.key == key))
        s = res.scalar_one_or_none()
        if s:
            s.value = value
        else:
            session.add(Setting(key=key, value=value))

    await _update_setting(SettingKeys.PAYMENT_CARD, card)
    await _update_setting(SettingKeys.PAYMENT_CARD_OWNER, owner)

    await session.commit()
    await state.clear()

    await message.answer(
        f"✅ <b>Karta muvaffaqiyatli yangilandi!</b>\n\n"
        f"💳 Karta raqami: <code>{card}</code>\n"
        f"👤 Karta egasi: {owner}"
    )

@router.callback_query(F.data == "admin_set_ref")
async def ask_ref(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🎁 <b>Yangi referal bonus foizini kiriting (masalan: 2):</b>")
    await state.set_state(AdminSettings.waiting_for_ref_pct)
    await callback.answer()

@router.message(AdminSettings.waiting_for_ref_pct, F.text)
async def process_ref(message: Message, state: FSMContext, session: AsyncSession):
    val = message.text.strip()
    res = await session.execute(select(Setting).where(Setting.key == SettingKeys.REFERRAL_PERCENT))
    s = res.scalar_one_or_none()
    if s: s.value = val
    else: session.add(Setting(key=SettingKeys.REFERRAL_PERCENT, value=val))
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Referal bonus {val}% etib belgilandi.")

@router.callback_query(F.data == "admin_set_cb")
async def ask_cb(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("💸 <b>Yangi keshbek foizini kiriting (masalan: 1):</b>")
    await state.set_state(AdminSettings.waiting_for_cb_pct)
    await callback.answer()

@router.message(AdminSettings.waiting_for_cb_pct, F.text)
async def process_cb(message: Message, state: FSMContext, session: AsyncSession):
    val = message.text.strip()
    res = await session.execute(select(Setting).where(Setting.key == SettingKeys.CASHBACK_PERCENT))
    s = res.scalar_one_or_none()
    if s: s.value = val
    else: session.add(Setting(key=SettingKeys.CASHBACK_PERCENT, value=val))
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Keshbek {val}% etib belgilandi.")

@router.callback_query(F.data == "admin_set_min_wd")
async def ask_min_wd(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("💰 <b>Minimal yechish summasini kiriting (masalan: 10000):</b>")
    await state.set_state(AdminSettings.waiting_for_min_withdraw)
    await callback.answer()

@router.message(AdminSettings.waiting_for_min_withdraw, F.text)
async def process_min_wd(message: Message, state: FSMContext, session: AsyncSession):
    val = message.text.strip()
    res = await session.execute(select(Setting).where(Setting.key == SettingKeys.MIN_WITHDRAWAL))
    s = res.scalar_one_or_none()
    if s: s.value = val
    else: session.add(Setting(key=SettingKeys.MIN_WITHDRAWAL, value=val))
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Minimal yechish {val} so'm etib belgilandi.")
