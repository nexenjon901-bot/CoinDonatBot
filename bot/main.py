import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from core.config import config
from core.logger import logger
from db.database import async_session
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.i18n import I18nMiddleware

# Handlerlar
from bot.handlers.registration import router as reg_router
from bot.handlers.shop import router as shop_router
from bot.handlers.balance import router as balance_router
from bot.handlers.profile import router as profile_router
from bot.handlers.referral import router as referral_router
from bot.handlers.useful import router as useful_router
from bot.handlers.orders import router as orders_router
from bot.handlers.admin import router as admin_router


async def main():
    logger.info("Bot ishga tushirilmoqda...")

    os.makedirs("bot/images", exist_ok=True)

    session = AiohttpSession(timeout=30.0)
    bot = Bot(
        token=config.BOT_TOKEN.get_secret_value(),
        session=session,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()

    dp.update.outer_middleware(DbSessionMiddleware(async_session))
    dp.update.outer_middleware(I18nMiddleware())

    # Routerlar
    dp.include_router(reg_router)
    dp.include_router(shop_router)
    dp.include_router(balance_router)
    dp.include_router(profile_router)
    dp.include_router(referral_router)
    dp.include_router(useful_router)
    dp.include_router(orders_router)
    dp.include_router(admin_router)

    while True:
        try:
            try:
                await bot.delete_webhook(drop_pending_updates=True)
            except Exception as e:
                logger.warning(f"Webhook o'chirishda ogohlantirish: {e}")
            logger.info("Telegram bilan ulanish o'rnatildi, polling boshlandi...")
            await dp.start_polling(bot, handle_signals=False)
        except Exception as e:
            logger.error(f"Tarmoq yoki ulanish xatosi: {e}. 3 soniyadan so'ng qayta uriniladi...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
