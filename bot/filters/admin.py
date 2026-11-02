from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from typing import Union
from core.config import config


class IsAdmin(BaseFilter):
    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        # Check against the master admin ID configured in .env
        # Later this can be expanded to check against the DB `admins` table
        return event.from_user.id == config.ADMIN_ID
