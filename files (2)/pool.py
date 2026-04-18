"""db/pool.py — Async MySQL connection pool + all DB operations."""

import logging
import os
import json
from datetime import datetime, timezone
import aiomysql
from db.schema import SCHEMA_SQL, DEFAULT_COMMANDS, DEFAULT_SETTINGS

logger = logging.getLogger(__name__)

# ── Pool factory ─────────────────────────────────────────────────────────────

async def create_pool() -> aiomysql.Pool:
    pool = await aiomysql.create_pool(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        db=os.getenv("MYSQL_DATABASE"),
        ssl={"ca": None},
        autocommit=True,
        minsize=2,
        maxsize=10,
        connect_timeout=10,
    )
    return pool


async def init_schema(pool: aiomysql.Pool):
    """Create all tables and seed defaults (idempotent)."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for statement in SCHEMA_SQL.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    await cur.execute(stmt)

    await _seed_commands(pool)
    await _seed_settings(pool)
    logger.info("Schema initialised.")


async def _seed_commands(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for (name, desc, cat, req_admin, sort) in DEFAULT_COMMANDS:
                await cur.execute("""
                    INSERT INTO COMMANDS (COMMAND_NAME, DESCRIPTION, CATEGORY, REQUIRES_ADMIN, SORT_ORDER)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        DESCRIPTION=VALUES(DESCRIPTION),
                        CATEGORY=VALUES(CATEGORY),
                        SORT_ORDER=VALUES(SORT_ORDER)
                """, (name, desc, cat, req_admin, sort))


async def _seed_settings(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for (key, val, desc) in DEFAULT_SETTINGS:
                await cur.execute("""
                    INSERT INTO BOT_SETTINGS (SETTING_KEY, SETTING_VALUE, DESCRIPTION)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE DESCRIPTION=VALUES(DESCRIPTION)
                """, (key, val, desc))


# ── Settings ─────────────────────────────────────────────────────────────────

async def get_setting(pool, key: str, default: str = "") -> str:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT SETTING_VALUE FROM BOT_SETTINGS WHERE SETTING_KEY=%s", (key,))
            row = await cur.fetchone()
            return row["SETTING_VALUE"] if row and row["SETTING_VALUE"] is not None else default


async def set_setting(pool, key: str, value: str, updated_by: int = None):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                INSERT INTO BOT_SETTINGS (SETTING_KEY, SETTING_VALUE, UPDATED_BY)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE SETTING_VALUE=%s, UPDATED_BY=%s
            """, (key, value, updated_by, value, updated_by))


async def get_all_settings(pool) -> list:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM BOT_SETTINGS ORDER BY SETTING_KEY")
            return await cur.fetchall()


# ── Commands ─────────────────────────────────────────────────────────────────

async def get_active_commands(pool, admin: bool = False) -> list:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            if admin:
                await cur.execute("SELECT * FROM COMMANDS WHERE IS_ACTIVE=1 ORDER BY SORT_ORDER")
            else:
                await cur.execute(
                    "SELECT * FROM COMMANDS WHERE IS_ACTIVE=1 AND REQUIRES_ADMIN=0 ORDER BY SORT_ORDER"
                )
            return await cur.fetchall()


async def get_command(pool, name: str) -> dict | None:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM COMMANDS WHERE COMMAND_NAME=%s", (name,))
            return await cur.fetchone()


async def toggle_command(pool, name: str) -> bool | None:
    """Toggle IS_ACTIVE. Returns new state or None if not found."""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT ID, IS_ACTIVE FROM COMMANDS WHERE COMMAND_NAME=%s", (name,))
            row = await cur.fetchone()
            if not row:
                return None
            new_state = not row["IS_ACTIVE"]
            await cur.execute("UPDATE COMMANDS SET IS_ACTIVE=%s WHERE ID=%s", (new_state, row["ID"]))
            return new_state


# ── Chat (upsert) ─────────────────────────────────────────────────────────────

async def upsert_chat(pool, chat) -> int:
    """Upsert from aiogram Chat object. Returns internal CHATS.ID."""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            title = getattr(chat, "title", None)
            username = getattr(chat, "username", None)
            await cur.execute("""
                INSERT INTO CHATS (TELEGRAM_CHAT_ID, CHAT_TYPE, TITLE, USERNAME)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    TITLE=VALUES(TITLE), USERNAME=VALUES(USERNAME),
                    UPDATED_AT=CURRENT_TIMESTAMP
            """, (chat.id, chat.type, title, username))
            await cur.execute("SELECT ID FROM CHATS WHERE TELEGRAM_CHAT_ID=%s", (chat.id,))
            row = await cur.fetchone()
            return row["ID"]


async def get_log_group_id(pool) -> int | None:
    val = await get_setting(pool, "LOG_GROUP_CHAT_ID", "")
    return int(val) if val.lstrip("-").isdigit() else None


async def set_log_group(pool, chat_id: int, updated_by: int = None):
    await set_setting(pool, "LOG_GROUP_CHAT_ID", str(chat_id), updated_by)


async def get_main_group_id(pool) -> int | None:
    val = await get_setting(pool, "MAIN_GROUP_CHAT_ID", "")
    return int(val) if val.lstrip("-").isdigit() else None


# ── User ─────────────────────────────────────────────────────────────────────

async def upsert_user(pool, tg_user) -> dict:
    """
    Insert or update from aiogram User object.
    Returns dict: {id, telegram_user_id, is_new}
    """
    full = " ".join(filter(None, [tg_user.first_name, tg_user.last_name])).strip() or None
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT ID, IS_ADMIN, ADMIN_LEVEL FROM TELEGRAM_USERS WHERE TELEGRAM_USER_ID=%s",
                (tg_user.id,)
            )
            existing = await cur.fetchone()

            if existing:
                await cur.execute("""
                    UPDATE TELEGRAM_USERS SET
                        USERNAME=%s, FIRST_NAME=%s, LAST_NAME=%s, FULL_NAME=%s,
                        LANGUAGE_CODE=%s, IS_BOT=%s,
                        IS_PREMIUM=%s, LAST_SEEN_AT=%s,
                        TOTAL_MESSAGES=TOTAL_MESSAGES+1,
                        UPDATED_AT=%s
                    WHERE TELEGRAM_USER_ID=%s
                """, (
                    tg_user.username, tg_user.first_name, tg_user.last_name, full,
                    tg_user.language_code, tg_user.is_bot,
                    getattr(tg_user, "is_premium", False), now,
                    now, tg_user.id,
                ))
                return {
                    "id": existing["ID"],
                    "telegram_user_id": tg_user.id,
                    "is_new": False,
                    "is_admin": existing["IS_ADMIN"],
                    "admin_level": existing["ADMIN_LEVEL"],
                }
            else:
                import secrets, string
                ref = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                await cur.execute("""
                    INSERT INTO TELEGRAM_USERS
                        (TELEGRAM_USER_ID, USERNAME, FIRST_NAME, LAST_NAME, FULL_NAME,
                         LANGUAGE_CODE, IS_BOT, IS_PREMIUM, REFERRAL_CODE,
                         LAST_SEEN_AT, CREATED_AT, UPDATED_AT)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    tg_user.id, tg_user.username, tg_user.first_name,
                    tg_user.last_name, full, tg_user.language_code,
                    tg_user.is_bot, getattr(tg_user, "is_premium", False),
                    ref, now, now, now,
                ))
                new_id = cur.lastrowid
                return {"id": new_id, "telegram_user_id": tg_user.id, "is_new": True,
                        "is_admin": False, "admin_level": 0}


async def get_user_by_telegram_id(pool, telegram_id: int) -> dict | None:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM TELEGRAM_USERS WHERE TELEGRAM_USER_ID=%s", (telegram_id,)
            )
            return await cur.fetchone()


async def get_user_by_id(pool, user_id: int) -> dict | None:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM TELEGRAM_USERS WHERE ID=%s", (user_id,))
            return await cur.fetchone()


async def get_all_users(pool, limit: int = 50, offset: int = 0) -> list:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("""
                SELECT ID, TELEGRAM_USER_ID, USERNAME, FULL_NAME, IS_ADMIN,
                       IS_BANNED, IS_ACTIVE, GENDER, CREATED_AT, LAST_SEEN_AT
                FROM TELEGRAM_USERS
                WHERE DELETED_AT IS NULL
                ORDER BY CREATED_AT DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
            return await cur.fetchall()


async def ban_user(pool, telegram_id: int, reason: str, by_admin_id: int) -> bool:
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            affected = await cur.execute("""
                UPDATE TELEGRAM_USERS SET IS_BANNED=1, BAN_REASON=%s
                WHERE TELEGRAM_USER_ID=%s AND IS_BANNED=0
            """, (reason, telegram_id))
            return affected > 0


async def unban_user(pool, telegram_id: int) -> bool:
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            affected = await cur.execute("""
                UPDATE TELEGRAM_USERS SET IS_BANNED=0, BAN_REASON=NULL
                WHERE TELEGRAM_USER_ID=%s
            """, (telegram_id,))
            return affected > 0


async def set_admin(pool, telegram_id: int, level: int = 2) -> bool:
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            affected = await cur.execute("""
                UPDATE TELEGRAM_USERS SET IS_ADMIN=%s, ADMIN_LEVEL=%s
                WHERE TELEGRAM_USER_ID=%s
            """, (level > 0, level, telegram_id))
            return affected > 0


async def set_user_gender(pool, telegram_id: int, gender: str) -> bool:
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            affected = await cur.execute(
                "UPDATE TELEGRAM_USERS SET GENDER=%s WHERE TELEGRAM_USER_ID=%s",
                (gender, telegram_id)
            )
            return affected > 0


# ── Stats ─────────────────────────────────────────────────────────────────────

async def get_stats(pool) -> dict:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(IS_ACTIVE)  AS active,
                    SUM(IS_BANNED)  AS banned,
                    SUM(IS_BLOCKED) AS blocked,
                    SUM(IS_ADMIN)   AS admins,
                    SUM(IS_PREMIUM) AS premium,
                    SUM(IS_BOT)     AS bots,
                    SUM(GENDER='male')   AS male_count,
                    SUM(GENDER='female') AS female_count,
                    SUM(GENDER='other')  AS other_gender,
                    SUM(GENDER IS NULL)  AS unknown_gender
                FROM TELEGRAM_USERS WHERE DELETED_AT IS NULL
            """)
            user_stats = await cur.fetchone()

            await cur.execute("SELECT COUNT(*) AS total FROM CHATS WHERE IS_ACTIVE=1")
            chat_stats = await cur.fetchone()

            await cur.execute("SELECT COUNT(*) AS total FROM USER_COMMAND_LOGS")
            cmd_stats = await cur.fetchone()

            await cur.execute("""
                SELECT COMMAND_NAME, COUNT(*) AS uses
                FROM USER_COMMAND_LOGS ucl
                JOIN COMMANDS c ON c.ID = ucl.COMMAND_ID
                GROUP BY COMMAND_ID ORDER BY uses DESC LIMIT 5
            """)
            top_cmds = await cur.fetchall()

            return {
                "users": user_stats,
                "chats": chat_stats,
                "commands": cmd_stats,
                "top_commands": top_cmds,
            }


# ── Command logging ───────────────────────────────────────────────────────────

async def log_command(pool, user_id: int, chat_db_id: int, command_name: str,
                      message_id: int = None, message_text: str = None,
                      status: str = "SUCCESS", error: str = None, exec_ms: int = 0):
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT ID FROM COMMANDS WHERE COMMAND_NAME=%s", (command_name,)
            )
            cmd = await cur.fetchone()
            if not cmd:
                return

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            await cur.execute("""
                INSERT INTO USER_COMMAND_LOGS
                    (USER_ID, CHAT_ID, COMMAND_ID, MESSAGE_ID, MESSAGE_TEXT,
                     STATUS, ERROR_MESSAGE, EXECUTION_MS, SENT_AT, CREATED_AT)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (user_id, chat_db_id, cmd["ID"], message_id, message_text,
                  status, error, exec_ms, now, now))

            # bump counter
            await cur.execute("""
                UPDATE TELEGRAM_USERS
                SET TOTAL_COMMANDS=TOTAL_COMMANDS+1, LAST_COMMAND_AT=%s
                WHERE ID=%s
            """, (now, user_id))


async def get_user_history(pool, user_db_id: int, limit: int = 10) -> list:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("""
                SELECT c.COMMAND_NAME, ucl.STATUS, ucl.SENT_AT, ucl.MESSAGE_TEXT
                FROM USER_COMMAND_LOGS ucl
                JOIN COMMANDS c ON c.ID = ucl.COMMAND_ID
                WHERE ucl.USER_ID=%s
                ORDER BY ucl.SENT_AT DESC LIMIT %s
            """, (user_db_id, limit))
            return await cur.fetchall()
