from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from typing import Callable


def get_catalog_keyboard(account_id: int, _: Callable[[str], str], is_favorite: bool, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Buy & Favorite
    builder.button(text=_("btn_buy"), callback_data=f"buy_{account_id}")
    fav_text = _("btn_remove_fav") if is_favorite else _("btn_add_fav")
    # pass page to return to same state
    builder.button(
        text=fav_text, callback_data=f"fav_{account_id}_{current_page}")

    # Pagination
    if current_page > 1:
        builder.button(text="⬅️ Orqaga",
                       callback_data=f"cat_page_{current_page - 1}")
    else:
        builder.button(text=" ", callback_data="noop")

    builder.button(text=f"{current_page} / {total_pages}",
                   callback_data="noop")

    if current_page < total_pages:
        builder.button(text="Oldinga ➡️",
                       callback_data=f"cat_page_{current_page + 1}")
    else:
        builder.button(text=" ", callback_data="noop")

    builder.adjust(2, 3)  # Row 1: 2 buttons, Row 2: 3 buttons
    return builder.as_markup()
