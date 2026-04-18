"""handlers/group.py — Join events: welcome message + log group notification."""

import logging
from aiogram import Router
from aiogram.types import ChatMemberUpdated, Message
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION

import db
from utils.helpers import display_name

logger = logging.getLogger(__name__)
router = Router()


@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_user_join(event: ChatMemberUpdated, pool, **_):
    user = event.new_chat_member.user
    if user.is_bot:
        return

    # Upsert user + chat
    rec = await db.upsert_user(pool, user)
    await db.upsert_chat(pool, event.chat)

    full_rec = await db.get_user_by_telegram_id(pool, user.id)
    name = display_name(user)
    username = f"@{user.username}" if user.username else "—"

    # ── 1. Welcome message in the main group (if enabled) ──────────────────
    welcome_enabled = await db.get_setting(pool, "WELCOME_ENABLED", "true")
    if welcome_enabled.lower() == "true":
        tpl = await db.get_setting(
            pool, "WELCOME_TEXT",
            "👋 Welcome, {name}!\n\nYour ID: <code>{telegram_id}</code>\nUSER_ID: <code>{user_id}</code>\n\nType /help to see commands."
        )
        welcome_text = tpl.format(
            name=name,
            username=username,
            telegram_id=user.id,
            user_id=full_rec["ID"] if full_rec else "—",
        )
        try:
            await event.bot.send_message(event.chat.id, welcome_text)
        except Exception as e:
            logger.warning(f"Could not send welcome to {event.chat.id}: {e}")

    # ── 2. Log to management/log group ────────────────────────────────────
    auto_log = await db.get_setting(pool, "AUTO_LOG_JOINS", "true")
    if auto_log.lower() != "true":
        return

    log_chat_id = await db.get_log_group_id(pool)
    if not log_chat_id:
        return

    gender = (full_rec.get("GENDER") or "unknown").title() if full_rec else "unknown"
    is_new = rec.get("is_new", False)

    log_msg = (
        f"👤 <b>New Member Joined</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Name: <b>{name}</b>\n"
        f"Username: {username}\n"
        f"Gender: {gender}\n\n"
        f"📱 <b>Telegram ID:</b> <code>{user.id}</code>\n"
        f"🗄  <b>System ID:</b> <code>{full_rec['ID'] if full_rec else '—'}</code>\n"
        f"🔖 <b>Referral:</b> <code>{full_rec.get('REFERRAL_CODE') or '—'}</code>\n\n"
        f"💬 <b>Group:</b> {event.chat.title or event.chat.id}\n"
        f"📋 <b>Status:</b> {'🆕 New user' if is_new else '🔄 Returning'}"
    )

    try:
        await event.bot.send_message(log_chat_id, log_msg)
    except Exception as e:
        logger.warning(f"Could not send to log group {log_chat_id}: {e}")


@router.message()
async def capture_any(message: Message, pool, **_):
    """Silently upsert every non-bot sender (already done by middleware, this is safety net)."""
    pass