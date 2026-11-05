import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery


class CallbackGuardMiddleware(BaseMiddleware):
    """
    Callback tugmalar uchun himoya:
    - bir xil tugma ishlab turganda yoki juda tez (0.7 soniya) qayta bosilsa, takroriy bosish o'tkazib yuboriladi
      (masalan, "Tasdiqlash" ikki marta bosilganda ikki marta xarid qilinmaydi);
    - har bir callback albatta javob oladi — tugmadagi "yuklanmoqda" belgisi qolib ketmaydi.
    """

    THROTTLE_SECONDS = 0.7

    def __init__(self):
        self._running: set[tuple[int, str]] = set()
        self._last: dict[tuple[int, str], float] = {}

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        key = (event.from_user.id, event.data or "")
        now = time.monotonic()

        if key in self._running or now - self._last.get(key, 0) < self.THROTTLE_SECONDS:
            try:
                await event.answer()
            except Exception:
                pass
            return None

        self._running.add(key)
        self._last[key] = now
        if len(self._last) > 5000:  # xotira to'lib ketmasligi uchun eskilarini tozalaymiz
            cutoff = now - 60
            self._last = {k: t for k, t in self._last.items() if t > cutoff}
        try:
            return await handler(event, data)
        finally:
            self._running.discard(key)
            try:
                await event.answer()  # handler javob bermagan bo'lsa — yuklanish belgisini yopadi
            except Exception:
                pass
