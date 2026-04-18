"""utils/permissions.py — Admin guard decorator."""

import functools
from aiogram.types import Message
import db


def admin_only(level: int = 1):
    """Decorator: only allow users with ADMIN_LEVEL >= level."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(message: Message, *args, **kwargs):
            pool = kwargs.get("pool") or (args[0] if args else None)
            # Try to get pool from kwargs passed by aiogram
            pool = kwargs.get("pool")
            db_user = kwargs.get("db_user")
            admin_level = db_user.get("admin_level", 0) if db_user else 0

            if admin_level < level:
                # Double-check from DB
                rec = await db.get_user_by_telegram_id(pool, message.from_user.id)
                if not rec or (rec.get("ADMIN_LEVEL") or 0) < level:
                    await message.answer("🚫 <b>Access denied.</b> Admin only.")
                    return
            return await func(message, *args, **kwargs)
        return wrapper
    return decorator
