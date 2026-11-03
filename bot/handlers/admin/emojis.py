from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.filters.admin import IsAdmin
from db.models.setting import Setting
from core.emojis import (
    EMOJI_LABELS,
    get_emoji_id,
    update_emoji_cache,
    extract_custom_emoji_id,
    format_header_emoji
)

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class EmojiAdminStates(StatesGroup):
    waiting_for_emoji = State()


def get_emojis_menu_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for key, label in EMOJI_LABELS.items():
        current_id = get_emoji_id(key)
        status = f"✅ ID: {current_id[:6]}..." if current_id else "⚪️ Standart"
        builder.button(
            text=f"{label} [{status}]",
            callback_data=f"adm_emoji_edit_{key}"
        )
    builder.button(text="🔙 Orqaga", callback_data="adm_emoji_back")
    builder.adjust(1)
    return builder


@router.message(F.text == "🌟 Premium Emojilar")
async def show_emojis_dashboard(message: Message, session: AsyncSession):
    from core.emojis import load_emojis_from_db
    await load_emojis_from_db(session)

    text = (
        "🌟 <b>Telegram Premium Emojilar Boshqaruvi</b>\n\n"
        "Bu yerda botning barcha tugmalari, sarlavhalari va postlari uchun "
        "Telegram Premium (custom) emojilarini o'rnatishingiz mumkin.\n\n"
        "💡 <i>Qanday o'rnatiladi?</i>\n"
        "Kerakli bo'limni tanlang va botga to'g'ridan-to'g'ri <b>Telegram Premium emojini xabar qilib yuboring</b> "
        "yoki uning raqamli <b>Custom Emoji ID</b> sini kiriting!\n\n"
        "O'zgartirmoqchi bo'lgan bo'limni tanlang:"
    )
    await message.answer(text, reply_markup=get_emojis_menu_keyboard().as_markup())


@router.callback_query(F.data == "adm_emoji_back")
async def back_to_emojis_menu(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("adm_emoji_edit_"))
async def start_emoji_edit(callback: CallbackQuery, state: FSMContext):
    key = callback.data.replace("adm_emoji_edit_", "")
    label = EMOJI_LABELS.get(key, key)
    current_id = get_emoji_id(key) or "O'rnatilmagan (standart)"

    await state.update_data(target_emoji_key=key)
    await state.set_state(EmojiAdminStates.waiting_for_emoji)

    text = (
        f"⚙️ <b>{label}</b> uchun Premium Emoji sozlash\n\n"
        f"📌 Joriy ID: <code>{current_id}</code>\n\n"
        f"👉 <b>Telegram Premium emojini xabar qilib yuboring</b>\n"
        f"yoki uning Custom Emoji ID raqamini kiriting.\n\n"
        f"• Bekor qilish: /cancel\n"
        f"• Standart holatga qaytarish: /clear"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="adm_emoji_cancel")
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "adm_emoji_cancel")
async def cancel_emoji_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = "🌟 <b>Telegram Premium Emojilar</b> ro'yxati:"
    await callback.message.edit_text(text, reply_markup=get_emojis_menu_keyboard().as_markup())
    await callback.answer()


@router.message(EmojiAdminStates.waiting_for_emoji)
async def process_emoji_input(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    key = data.get("target_emoji_key")

    if not key:
        await state.clear()
        await message.answer("Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        return

    # Bekor qilish
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi.")
        return

    db_key = f"emoji_{key}"

    # Standart holatga tozalash
    if message.text == "/clear":
        res = await session.execute(select(Setting).where(Setting.key == db_key))
        s = res.scalar_one_or_none()
        if s:
            s.value = ""
        await session.commit()
        update_emoji_cache(key, "")
        await state.clear()
        await message.answer(
            f"✅ <b>{EMOJI_LABELS.get(key, key)}</b> standart holatga qaytarildi!",
            reply_markup=get_emojis_menu_keyboard().as_markup()
        )
        return

    # Premium emoji ID ni ajratib olish
    emoji_id, fallback = extract_custom_emoji_id(message)

    if not emoji_id:
        await message.answer(
            "⚠️ <b>Telegram Premium emoji topilmadi!</b>\n\n"
            "Iltimos, Telegram Premium stiker/emojisini yuboring yoki uning ID raqamini kiriting.\n"
            "Chiqish uchun /cancel bosing."
        )
        return

    # Bazada saqlash
    res = await session.execute(select(Setting).where(Setting.key == db_key))
    setting_row = res.scalar_one_or_none()
    if setting_row:
        setting_row.value = emoji_id
    else:
        session.add(Setting(key=db_key, value=emoji_id))

    await session.commit()
    update_emoji_cache(key, emoji_id)
    await state.clear()

    preview = f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    await message.answer(
        f"✅ <b>{EMOJI_LABELS.get(key, key)}</b> muvaffaqiyatli saqlandi!\n\n"
        f"🌟 Ko'rinishi: {preview}\n"
        f"🔑 Custom Emoji ID: <code>{emoji_id}</code>\n\n"
        f"Endi bot ushbu emojini tugmalar va sarlavhalarda ishlatadi.",
        reply_markup=get_emojis_menu_keyboard().as_markup()
    )
