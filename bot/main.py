import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from core.config import config
from core.logger import logger
from db.database import async_session
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.i18n import I18nMiddleware
from bot.middlewares.premium_emoji import PremiumEmojiMiddleware

# Handlerlar
from bot.handlers.registration import router as reg_router
from bot.handlers.shop import router as shop_router
from bot.handlers.balance import router as balance_router
from bot.handlers.profile import router as profile_router
from bot.handlers.referral import router as referral_router
from bot.handlers.useful import router as useful_router
from bot.handlers.admin import router as admin_router
from bot.handlers.errors import router as errors_router
from bot.middlewares.callback_guard import CallbackGuardMiddleware


async def start_bot():
    os.makedirs("bot/images", exist_ok=True)

    # Bazadagi jadvallarni avtomatik tekshirish va yaratish
    try:
        from init_db import init_db
        from core.emojis import load_emojis_from_db
        logger.info("Ma'lumotlar bazasi jadvallarini tekshirish va yaratish...")
        await init_db()
        logger.info("Baza jadvallari muvaffaqiyatli tayyorlandi!")

        async with async_session() as session:
            await load_emojis_from_db(session)
        logger.info("Telegram Premium emojilar bazadan yuklandi!")
    except Exception as e:
        logger.error(f"Initsializatsiyada xatolik: {e}")

    dp = Dispatcher()
    dp.update.outer_middleware(DbSessionMiddleware(async_session))
    dp.update.outer_middleware(I18nMiddleware())
    dp.callback_query.outer_middleware(CallbackGuardMiddleware())

    # Routerlar
    dp.include_router(errors_router)
    dp.include_router(reg_router)
    dp.include_router(shop_router)
    dp.include_router(balance_router)
    dp.include_router(profile_router)
    dp.include_router(referral_router)
    dp.include_router(useful_router)
    dp.include_router(admin_router)

    while True:
        bot = Bot(
            token=config.BOT_TOKEN.get_secret_value(),
            default=DefaultBotProperties(parse_mode="HTML")
        )
        bot.session.middleware(PremiumEmojiMiddleware())
        try:
            me = await bot.get_me()
            logger.info(f"Botga ulandi: @{me.username} (ID: {me.id})")
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Polling boshlandi...")
            await dp.start_polling(
                bot,
                handle_signals=False,
                polling_timeout=20,
                allowed_updates=["message", "callback_query"]
            )
        except Exception as e:
            logger.error(f"Ulanish yoki polling xatosi: {e}. 3 soniyadan so'ng qayta ulanadi...")
            await asyncio.sleep(3)
        finally:
            try:
                await bot.session.close()
            except Exception:
                pass


def main():
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    main()
