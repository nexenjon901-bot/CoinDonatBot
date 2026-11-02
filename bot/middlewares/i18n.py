import json
import os
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from sqlalchemy import select
from db.models.user import User


class I18nMiddleware(BaseMiddleware):
    def __init__(self, default_lang: str = "uz"):
        self.default_lang = default_lang
        self.locales = {}
        self._load_locales()

    def _load_locales(self):
        locales_dir = os.path.join(os.path.dirname(__file__), "..", "locales")
        for lang in ["uz", "ru", "en"]:
            path = os.path.join(locales_dir, lang, "messages.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self.locales[lang] = json.load(f)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session = data.get("session")
        tg_user: TgUser = data.get("event_from_user")
        lang = self.default_lang
        db_user = None

        if tg_user and session:
            result = await session.execute(select(User).where(User.telegram_id == tg_user.id))
            db_user = result.scalar_one_or_none()
            if db_user:
                lang = db_user.language

        data["db_user"] = db_user
        data["lang"] = lang

        def _(key: str) -> str:
            return self.locales.get(lang, {}).get(key, key)

        data["_"] = _
        return await handler(event, data)
