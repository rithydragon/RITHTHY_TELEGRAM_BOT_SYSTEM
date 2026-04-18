"""utils/helpers.py"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import db


def display_name(user) -> str:
    parts = [getattr(user, "first_name", "") or "", getattr(user, "last_name", "") or ""]
    return " ".join(p for p in parts if p).strip() or getattr(user, "username", None) or "Unknown"


def fmt_user(rec: dict) -> str:
    un = f"@{rec['USERNAME']}" if rec.get("USERNAME") else "—"
    name = rec.get("FULL_NAME") or "—"
    gender_icon = {"male": "♂️", "female": "♀️", "other": "⚧️"}.get(
        (rec.get("GENDER") or "").lower(), "❓"
    )
    banned = "🚫 BANNED" if rec.get("IS_BANNED") else ("✅ Active" if rec.get("IS_ACTIVE") else "⛔ Inactive")
    admin_badge = f" 🛡️ L{rec['ADMIN_LEVEL']}" if rec.get("IS_ADMIN") else ""
    return (
        f"👤 <b>{name}</b>{admin_badge} {gender_icon}\n"
        f"   Username: {un}\n"
        f"   ID: <code>{rec['TELEGRAM_USER_ID']}</code>  |  DB: <code>{rec['ID']}</code>\n"
        f"   Status: {banned}"
    )


def paginate_text(lines: list[str], header: str, page_size: int = 3500) -> list[str]:
    pages, chunk = [], []
    current = header + "\n\n"
    for line in lines:
        if len(current) + len(line) + 2 > page_size:
            pages.append(current)
            current = line + "\n"
        else:
            current += line + "\n"
    if current.strip():
        pages.append(current)
    return pages


def gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="♂️ Male",   callback_data="gender_male"),
        InlineKeyboardButton(text="♀️ Female", callback_data="gender_female"),
        InlineKeyboardButton(text="⚧️ Other",  callback_data="gender_other"),
    ]])


def confirm_keyboard(action: str, target_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm_{action}_{target_id}"),
        InlineKeyboardButton(text="❌ Cancel",  callback_data="cancel_action"),
    ]])