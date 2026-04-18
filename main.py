"""main.py — Entry point."""

import asyncio
import logging
import os
from dotenv import load_dotenv
from bot import create_bot

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("🚀 Starting Agriculture Telegram Bot...")
    bot, dp, pool = await create_bot()
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        pool.close()
        await pool.wait_closed()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
