import secrets
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.states.registration import Registration
from db.models.user import User
from typing import Callable
from core.config import config

router = Router()

MAIN_MENU_BANNER = "bot/images/menu.png"


def get_main_menu_keyboard(_: Callable[[str], str], is_admin: bool = False):
    """Asosiy menyu - inline keyboard (Telegram Premium emoji bilan)"""
    from core.emojis import create_button
    builder = InlineKeyboardBuilder()
    # row 1
    builder.add(create_button("Do'kon", emoji_key="shop", callback_data="menu_shop"))
    # row 2
    builder.add(create_button("Profil", emoji_key="profile", callback_data="menu_profile"))
    builder.add(create_button("To'ldirish", emoji_key="balance", callback_data="menu_balance"))
    # row 3
    builder.add(create_button("Foydali", emoji_key="useful", callback_data="menu_useful"))
    builder.add(create_button("Referal tizimi", emoji_key="referral", callback_data="menu_referral"))
    # row 4 — URL button for support
    builder.add(create_button("Qo'llab-quvvatlash ↗", emoji_key="support", url=config.SUPPORT_URL))
    if is_admin:
        # row 5
        builder.add(create_button("Admin panel", emoji_key="admin", callback_data="menu_admin"))
        builder.adjust(1, 2, 2, 1, 1)
    else:
        builder.adjust(1, 2, 2, 1)
    return builder.as_markup()


def _generate_referral_code(telegram_id: int) -> str:
    """Unikal referal kod yaratish"""
    return f"REF{telegram_id % 100000:05d}{secrets.token_hex(2).upper()}"


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext, session: AsyncSession, db_user: User, _: Callable[[str], str]):
    is_admin = message.from_user.id == config.ADMIN_ID

    if db_user:
        # Referal kodi yo'q bo'lsa — yaratib qo'yamiz
        if not db_user.referral_code:
            db_user.referral_code = _generate_referral_code(
                message.from_user.id)
            session.add(db_user)
            await session.commit()

        from core.ui import answer_with_banner, main_menu_caption
        await answer_with_banner(
            message,
            banner_path=MAIN_MENU_BANNER,
            text=main_menu_caption(db_user.first_name),
            reply_markup=get_main_menu_keyboard(_, is_admin=is_admin),
        )
        return

    # Ro'yxatdan o'tmagan — til tanlash
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbek tili", callback_data="lang_uz")
    builder.button(text="🇷🇺 Русский",      callback_data="lang_ru")
    builder.button(text="🇬🇧 English",      callback_data="lang_en")
    builder.adjust(1)

    # Agar /start ref_XXX bilan kelsa — referal kodi saqlash
    args = message.text.split() if message.text else []
    ref_code = args[1] if len(args) > 1 else None
    if ref_code:
        await state.update_data(ref_code=ref_code)

    welcome_text = (
        "👋 <b>Xush kelibsiz! / Добро пожаловать! / Welcome!</b>\n\n"
        "🪙 <b>COIN DONAT BOT</b> — O'zbekistonning eng ishonchli PUBG UC va akkauntlar savdo markazi.\n\n"
        "🌐 Iltimos, o'zingizga qulay tilni tanlang:\n"
        "🌐 Пожалуйста, выберите удобный для вас язык:\n"
        "🌐 Please select your preferred language:"
    )

    await message.answer(welcome_text, reply_markup=builder.as_markup())
    await state.set_state(Registration.language_selection)


@router.callback_query(Registration.language_selection, F.data.startswith("lang_"))
async def language_selected(callback: CallbackQuery, state: FSMContext):
    lang_code = callback.data.split("_")[1]
    await state.update_data(selected_lang=lang_code)

    msgs = {
        "uz": ("📱 <b>Ro'yxatdan o'tish</b>\n\nCoin Donat Bot'dan foydalanish uchun telefon raqamingizni yuboring.", "📱 Telefon raqamni yuborish"),
        "ru": ("📱 <b>Регистрация</b>\n\nПожалуйста, отправьте свой номер телефона.", "📱 Отправить номер"),
        "en": ("📱 <b>Registration</b>\n\nPlease share your phone number to continue.", "📱 Send Phone Number"),
    }
    text, btn_text = msgs[lang_code]

    phone_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=btn_text, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.delete()
    await callback.message.answer(text, reply_markup=phone_kb)
    await state.set_state(Registration.phone_number)


@router.message(Registration.phone_number, F.contact)
async def phone_received(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("selected_lang", "uz")
    ref_code = data.get("ref_code")

    # Referal kodi tekshirish — kim taklif qilganini topamiz
    referred_by = None
    if ref_code:
        from sqlalchemy import select
        ref_result = await session.execute(
            select(User).where(User.referral_code == ref_code)
        )
        ref_user = ref_result.scalar_one_or_none()
        if ref_user and ref_user.telegram_id != message.from_user.id:
            referred_by = ref_code
            # Prompt bo'yicha: srazu bonus berilmaydi (firibgarlik oldini olish)

    new_user = User(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        phone_number=message.contact.phone_number,
        language=lang,
        referral_code=_generate_referral_code(message.from_user.id),
        referred_by=referred_by,
    )
    session.add(new_user)
    await session.commit()

    success_msg = {
        "uz": "✅ <b>Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!</b>\n\nAsosiy menyuni ochish uchun /start bosing.",
        "ru": "✅ <b>Регистрация успешно завершена!</b>\n\nНажмите /start чтобы открыть главное меню.",
        "en": "✅ <b>Registration completed successfully!</b>\n\nPress /start to open the main menu.",
    }

    await message.answer(success_msg[lang], reply_markup=ReplyKeyboardRemove())
    await state.clear()


# ───────────────────────────────────────────
# INLINE MENU CALLBACK HANDLERS
# ───────────────────────────────────────────

@router.callback_query(F.data == "menu_shop")
async def menu_shop(callback: CallbackQuery, session: AsyncSession, db_user: User, _: Callable[[str], str]):
    from bot.handlers.shop import show_shop
    await callback.message.delete()
    await show_shop(callback.message, session, db_user, _)
    await callback.answer()


@router.callback_query(F.data == "menu_profile")
async def menu_profile(callback: CallbackQuery, session: AsyncSession, db_user: User, _: Callable[[str], str]):
    from bot.handlers.profile import show_profile
    await callback.message.delete()
    await show_profile(callback.message, session, db_user)
    await callback.answer()


@router.callback_query(F.data == "menu_balance")
async def menu_balance(callback: CallbackQuery, db_user: User):
    from bot.handlers.balance import show_balance_menu
    await callback.message.delete()
    await show_balance_menu(callback.message, db_user)
    await callback.answer()


@router.callback_query(F.data == "menu_useful")
async def menu_useful(callback: CallbackQuery):
    from bot.handlers.useful import show_useful
    await callback.message.delete()
    await show_useful(callback.message)
    await callback.answer()


@router.callback_query(F.data == "menu_referral")
async def menu_referral(callback: CallbackQuery, session: AsyncSession, db_user: User):
    from bot.handlers.referral import show_referral
    await callback.message.delete()
    await show_referral(callback.message, session, db_user)
    await callback.answer()


@router.callback_query(F.data == "menu_admin")
async def menu_admin(callback: CallbackQuery):
    from bot.handlers.admin.base import admin_menu
    await callback.message.delete()
    await admin_menu(callback.message)
    await callback.answer()
