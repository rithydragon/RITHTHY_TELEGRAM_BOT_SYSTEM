"""bot.py — Bot + Dispatcher factory."""

import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import db
from middlewares.base import UserMiddleware, CommandLogMiddleware
from handlers import user, admin, group

logger = logging.getLogger(__name__)


async def create_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment.")

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # ── Database ──────────────────────────────────────────────────────────
    pool = await db.create_pool()
    await db.init_schema(pool)
    logger.info("Database ready.")

    # ── Dispatcher ────────────────────────────────────────────────────────
    dp = Dispatcher()

    # Inject pool into every handler via data dict
    dp["pool"] = pool

    # Middlewares (order matters: UserMiddleware first, then log)
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())
    dp.message.middleware(CommandLogMiddleware())

    # Routers
    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(group.router)

    logger.info("Bot ready.")
    return bot, dp, pool
