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
    waiting_for_phone = State()
    waiting_for_support_url = State()
    waiting_for_channel_link = State()
    waiting_for_usd_rate = State()
    waiting_for_ref_pct = State()
    waiting_for_cb_pct = State()
    waiting_for_min_withdraw = State()


async def _get_val(session: AsyncSession, key: str, default: str) -> str:
    res = await session.execute(select(Setting).where(Setting.key == key))
    s = res.scalar_one_or_none()
    return s.value if s else default


async def _set_val(session: AsyncSession, key: str, value: str):
    res = await session.execute(select(Setting).where(Setting.key == key))
    s = res.scalar_one_or_none()
    if s:
        s.value = value
    else:
        session.add(Setting(key=key, value=value))


@router.message(F.text == "⚙️ Sozlamalar")
async def show_settings(message: Message, session: AsyncSession):
    card_val = await _get_val(session, SettingKeys.PAYMENT_CARD, "Kiritilmagan")
    owner_val = await _get_val(session, SettingKeys.PAYMENT_CARD_OWNER, "Kiritilmagan")
    phone_val = await _get_val(session, SettingKeys.PAYMENT_PHONE, "Kiritilmagan")
    support_url = await _get_val(session, SettingKeys.SUPPORT_URL, "Kiritilmagan")
    channel_link = await _get_val(session, SettingKeys.CHANNEL_LINK, "Kiritilmagan")
    usd_rate = await _get_val(session, SettingKeys.USD_RATE, "11880")
    ref_pct = await _get_val(session, SettingKeys.REFERRAL_PERCENT, "2")
    cb_pct = await _get_val(session, SettingKeys.CASHBACK_PERCENT, "1")
    min_wd = await _get_val(session, SettingKeys.MIN_WITHDRAWAL, "10000")

    text = (
        f"⚙️ <b>Bot sozlamalari</b>\n\n"
        f"💳 <b>Karta raqami:</b> <code>{card_val}</code>\n"
        f"👤 <b>Karta egasi:</b> {owner_val}\n"
        f"📱 <b>To'lov telefoni:</b> {phone_val}\n\n"
        f"🌐 <b>Qo'llab-quvvatlash:</b> {support_url}\n"
        f"📢 <b>Kanal havolasi:</b> {channel_link}\n\n"
        f"💱 <b>USD kursi:</b> {usd_rate} so'm/$\n"
        f"🎁 <b>Referal bonus:</b> {ref_pct}%\n"
        f"💸 <b>Xaridor keshbeki:</b> {cb_pct}%\n"
        f"💰 <b>Minimal yechish:</b> {min_wd} so'm\n\n"
        f"O'zgartirish uchun quyidagi tugmani bosing."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Karta ma'lumotlari", callback_data="admin_set_card")
    builder.button(text="📱 To'lov telefoni", callback_data="admin_set_phone")
    builder.button(text="🌐 Qo'llab-quvvatlash URL", callback_data="admin_set_support")
    builder.button(text="📢 Kanal havolasi", callback_data="admin_set_channel")
    builder.button(text="💱 USD kursi", callback_data="admin_set_usd_rate")
    builder.button(text="🎁 Referal bonusni o'zgartirish", callback_data="admin_set_ref")
    builder.button(text="💸 Keshbekni o'zgartirish", callback_data="admin_set_cb")
    builder.button(text="💰 Min. yechishni o'zgartirish", callback_data="admin_set_min_wd")
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup())


# ── KARTA ──────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_set_card")
async def ask_card(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "💳 <b>Yangi karta raqamini kiriting:</b>\n\n<i>Masalan: 4067 **** **** 1951</i>"
    )
    await state.set_state(AdminSettings.waiting_for_card)
    await callback.answer()


@router.message(AdminSettings.waiting_for_card, F.text)
async def process_card(message: Message, state: FSMContext):
    await state.update_data(card=message.text.strip())
    await message.answer("👤 <b>Karta egasining ismini kiriting:</b>\n\n<i>Masalan: S.Y (HUMO CARD)</i>")
    await state.set_state(AdminSettings.waiting_for_card_owner)


@router.message(AdminSettings.waiting_for_card_owner, F.text)
async def process_card_owner(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    card = data.get("card")
    owner = message.text.strip()

    await _set_val(session, SettingKeys.PAYMENT_CARD, card)
    await _set_val(session, SettingKeys.PAYMENT_CARD_OWNER, owner)
    await session.commit()
    await state.clear()

    await message.answer(
        f"✅ <b>Karta muvaffaqiyatli yangilandi!</b>\n\n"
        f"💳 Karta raqami: <code>{card}</code>\n"
        f"👤 Karta egasi: {owner}"
    )


# ── TO'LOV TELEFONI ─────────────────────────────────────────────

@router.callback_query(F.data == "admin_set_phone")
async def ask_phone(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📱 <b>To'lov uchun telefon raqamini kiriting:</b>\n\n<i>Masalan: 909610021</i>"
    )
    await state.set_state(AdminSettings.waiting_for_phone)
    await callback.answer()


@router.message(AdminSettings.waiting_for_phone, F.text)
async def process_phone(message: Message, state: FSMContext, session: AsyncSession):
    phone = message.text.strip()
    await _set_val(session, SettingKeys.PAYMENT_PHONE, phone)
    await session.commit()
    await state.clear()
    await message.answer(f"✅ To'lov telefoni yangilandi: <code>{phone}</code>")


# ── QOLLLAB-QUVVATLASH URL ──────────────────────────────────────

@router.callback_query(F.data == "admin_set_support")
async def ask_support(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🌐 <b>Qo'llab-quvvatlash havolasini kiriting:</b>\n\n<i>Masalan: https://t.me/coindonat_support</i>"
    )
    await state.set_state(AdminSettings.waiting_for_support_url)
    await callback.answer()


@router.message(AdminSettings.waiting_for_support_url, F.text)
async def process_support(message: Message, state: FSMContext, session: AsyncSession):
    url = message.text.strip()
    await _set_val(session, SettingKeys.SUPPORT_URL, url)
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Qo'llab-quvvatlash havolasi yangilandi: {url}")


# ── KANAL HAVOLASI ──────────────────────────────────────────────

@router.callback_query(F.data == "admin_set_channel")
async def ask_channel(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📢 <b>Chegirmalar kanal havolasini kiriting:</b>\n\n<i>Masalan: https://t.me/coindonat_support</i>"
    )
    await state.set_state(AdminSettings.waiting_for_channel_link)
    await callback.answer()


@router.message(AdminSettings.waiting_for_channel_link, F.text)
async def process_channel(message: Message, state: FSMContext, session: AsyncSession):
    url = message.text.strip()
    await _set_val(session, SettingKeys.CHANNEL_LINK, url)
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Kanal havolasi yangilandi: {url}")


# ── USD KURSI ────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_set_usd_rate")
async def ask_usd_rate(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "💱 <b>USD kursini kiriting (so'm):</b>\n\n<i>Masalan: 11880</i>"
    )
    await state.set_state(AdminSettings.waiting_for_usd_rate)
    await callback.answer()


@router.message(AdminSettings.waiting_for_usd_rate, F.text)
async def process_usd_rate(message: Message, state: FSMContext, session: AsyncSession):
    val = message.text.strip()
    if not val.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return
    await _set_val(session, SettingKeys.USD_RATE, val)
    await session.commit()
    await state.clear()
    await message.answer(f"✅ USD kursi yangilandi: {int(val):,} so'm/$")


# ── REFERAL FOIZ ─────────────────────────────────────────────────

@router.callback_query(F.data == "admin_set_ref")
async def ask_ref(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🎁 <b>Yangi referal bonus foizini kiriting (masalan: 2):</b>")
    await state.set_state(AdminSettings.waiting_for_ref_pct)
    await callback.answer()


@router.message(AdminSettings.waiting_for_ref_pct, F.text)
async def process_ref(message: Message, state: FSMContext, session: AsyncSession):
    val = message.text.strip()
    await _set_val(session, SettingKeys.REFERRAL_PERCENT, val)
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Referal bonus {val}% etib belgilandi.")


# ── KESHBEK FOIZ ──────────────────────────────────────────────────

@router.callback_query(F.data == "admin_set_cb")
async def ask_cb(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("💸 <b>Yangi keshbek foizini kiriting (masalan: 1):</b>")
    await state.set_state(AdminSettings.waiting_for_cb_pct)
    await callback.answer()


@router.message(AdminSettings.waiting_for_cb_pct, F.text)
async def process_cb(message: Message, state: FSMContext, session: AsyncSession):
    val = message.text.strip()
    await _set_val(session, SettingKeys.CASHBACK_PERCENT, val)
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Keshbek {val}% etib belgilandi.")


# ── MINIMAL YECHISH ──────────────────────────────────────────────

@router.callback_query(F.data == "admin_set_min_wd")
async def ask_min_wd(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("💰 <b>Minimal yechish summasini kiriting (masalan: 10000):</b>")
    await state.set_state(AdminSettings.waiting_for_min_withdraw)
    await callback.answer()


@router.message(AdminSettings.waiting_for_min_withdraw, F.text)
async def process_min_wd(message: Message, state: FSMContext, session: AsyncSession):
    val = message.text.strip()
    if not val.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return
    await _set_val(session, SettingKeys.MIN_WITHDRAWAL, val)
    await session.commit()
    await state.clear()
    await message.answer(f"✅ Minimal yechish {int(val):,} so'm etib belgilandi.")
