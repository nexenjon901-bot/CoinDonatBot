from aiogram.client.session.middlewares.base import BaseRequestMiddleware

from core.emojis import apply_premium_emojis
from core.logger import logger


class PremiumEmojiMiddleware(BaseRequestMiddleware):
    """
    Telegram'ga ketayotgan har bir xabar/tugmadagi standart emojilarni,
    admin panelda ID o'rnatilgan bo'lsa, Premium emojiga almashtiradi.
    Xatolik bo'lsa — xabar o'zgartirilmasdan yuboriladi.
    """

    async def __call__(self, make_request, bot, method):
        try:
            apply_premium_emojis(method)
        except Exception as e:
            logger.debug(f"Premium emoji qo'llanmadi: {e}")
        return await make_request(bot, method)
