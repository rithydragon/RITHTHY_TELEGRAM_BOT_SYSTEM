"""middlewares/base.py — Auth, ban-check, auto-register, command logging."""

import time
import logging
from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
import db

logger = logging.getLogger(__name__)


class UserMiddleware(BaseMiddleware):
    """
    For every update:
      1. Upsert user + chat into DB
      2. Reject banned users
      3. Attach db_user / db_chat_id / pool to handler data
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        pool = data.get("pool")
        if not pool:
            return await handler(event, data)

        # Resolve user & chat from event
        user = None
        chat = None
        if isinstance(event, Message):
            user = event.from_user
            chat = event.chat
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            chat = event.message.chat if event.message else None

        if user and not user.is_bot:
            try:
                rec = await db.upsert_user(pool, user)
                data["db_user"] = rec
                data["db_user_id"] = rec["id"]
                data["is_admin"] = rec.get("is_admin") or rec.get("admin_level", 0) > 0

                # Block banned users
                full_rec = await db.get_user_by_telegram_id(pool, user.id)
                if full_rec and full_rec.get("IS_BANNED"):
                    reason = full_rec.get("BAN_REASON") or "No reason provided"
                    if isinstance(event, Message):
                        await event.answer(f"🚫 You are banned.\nReason: {reason}")
                    elif isinstance(event, CallbackQuery):
                        await event.answer(f"🚫 Banned: {reason}", show_alert=True)
                    return  # stop pipeline

                if chat:
                    chat_id = await db.upsert_chat(pool, chat)
                    data["db_chat_id"] = chat_id

            except Exception as e:
                logger.error(f"UserMiddleware error: {e}")

        return await handler(event, data)


class CommandLogMiddleware(BaseMiddleware):
    """Log every /command to USER_COMMAND_LOGS."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        start = time.monotonic()
        result = await handler(event, data)
        elapsed = int((time.monotonic() - start) * 1000)

        if not isinstance(event, Message):
            return result
        if not event.text or not event.text.startswith("/"):
            return result

        pool = data.get("pool")
        user_db_id = data.get("db_user_id")
        chat_db_id = data.get("db_chat_id")
        if not (pool and user_db_id and chat_db_id):
            return result

        cmd = event.text.split()[0].lstrip("/").split("@")[0].lower()
        try:
            await db.log_command(
                pool, user_db_id, chat_db_id, cmd,
                message_id=event.message_id,
                message_text=event.text[:500],
                exec_ms=elapsed,
            )
        except Exception as e:
            logger.warning(f"CommandLogMiddleware: {e}")

        return result
