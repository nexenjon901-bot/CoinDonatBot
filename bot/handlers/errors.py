from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ErrorEvent

from core.config import config
from core.logger import logger

router = Router()

_IGNORED = (
    "message is not modified",
    "query is too old",
    "query id is invalid",
    "message to edit not found",
    "message can't be edited",
)


@router.errors()
async def global_error_handler(event: ErrorEvent, bot: Bot) -> bool:
    """Kutilmagan xatolar: foydalanuvchiga tushunarli javob, adminga qisqa xabar, logga to'liq iz."""
    exc = event.exception

    if isinstance(exc, TelegramBadRequest) and any(s in str(exc).lower() for s in _IGNORED):
        return True
    if isinstance(exc, TelegramForbiddenError):  # foydalanuvchi botni bloklagan
        return True

    logger.exception(f"Handler xatosi: {exc!r}")

    update = event.update
    try:
        if update.callback_query:
            await update.callback_query.answer(
                "⚠️ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", show_alert=True
            )
        elif update.message:
            await update.message.answer("⚠️ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
    except Exception:
        pass

    try:
        who = (update.callback_query or update.message)
        uid = who.from_user.id if who and who.from_user else "?"
        detail = (update.callback_query.data if update.callback_query else (update.message.text if update.message else ""))
        await bot.send_message(
            config.ADMIN_ID,
            f"🚨 <b>Bot xatosi</b>\n\n<code>{type(exc).__name__}: {str(exc)[:300]}</code>\n"
            f"Foydalanuvchi: <code>{uid}</code>\nAmal: <code>{(detail or '')[:100]}</code>",
        )
    except Exception:
        pass
    return True
