import logging
import os
import aiomysql

logger = logging.getLogger(__name__)


async def get_pool():
    pool = await aiomysql.create_pool(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        db=os.getenv("MYSQL_DATABASE"),
        # ssl={"ca": None},
        autocommit=True,
        minsize=1,
        maxsize=5,
    )
    return pool


async def ensure_users_table(pool):
    """Create a minimal USERS table if it doesn't exist (required by FK)."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS USERS (
                    ID BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("USERS table ensured.")


async def ensure_telegram_users_table(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS TELEGRAM_USERS (
                    ID BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    USER_ID BIGINT UNSIGNED NOT NULL,
                    TELEGRAM_ID BIGINT NOT NULL,
                    USERNAME VARCHAR(255),
                    FIRST_NAME VARCHAR(255),
                    LAST_NAME VARCHAR(255),
                    LANGUAGE_CODE VARCHAR(10),
                    IS_BOT TINYINT(1) DEFAULT 0,
                    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY UK_TELEGRAM_ID (TELEGRAM_ID),
                    UNIQUE KEY UK_USER_ID (USER_ID),
                    CONSTRAINT FK_TELEGRAM_USER_SYSTEM_USER
                        FOREIGN KEY (USER_ID)
                        REFERENCES USERS(ID)
                        ON DELETE CASCADE
                )
            """)
            logger.info("TELEGRAM_USERS table ensured.")


async def upsert_telegram_user(pool, tg_user) -> dict:
    """
    Insert or update a Telegram user.
    Returns a dict with user_id, telegram_id, is_new.
    """
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Check if telegram user exists
            await cur.execute(
                "SELECT ID, USER_ID, TELEGRAM_ID FROM TELEGRAM_USERS WHERE TELEGRAM_ID = %s",
                (tg_user.id,)
            )
            existing = await cur.fetchone()

            if existing:
                # Update
                await cur.execute("""
                    UPDATE TELEGRAM_USERS
                    SET USERNAME=%s, FIRST_NAME=%s, LAST_NAME=%s,
                        LANGUAGE_CODE=%s, IS_BOT=%s
                    WHERE TELEGRAM_ID=%s
                """, (
                    tg_user.username,
                    tg_user.first_name,
                    tg_user.last_name,
                    tg_user.language_code,
                    int(tg_user.is_bot),
                    tg_user.id,
                ))
                return {"user_id": existing["USER_ID"], "telegram_id": tg_user.id, "is_new": False}
            else:
                # Create system user first
                await cur.execute("INSERT INTO USERS () VALUES ()")
                system_user_id = cur.lastrowid

                # Insert telegram user
                await cur.execute("""
                    INSERT INTO TELEGRAM_USERS
                        (USER_ID, TELEGRAM_ID, USERNAME, FIRST_NAME, LAST_NAME, LANGUAGE_CODE, IS_BOT)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    system_user_id,
                    tg_user.id,
                    tg_user.username,
                    tg_user.first_name,
                    tg_user.last_name,
                    tg_user.language_code,
                    int(tg_user.is_bot),
                ))
                return {"user_id": system_user_id, "telegram_id": tg_user.id, "is_new": True}


async def get_all_users(pool) -> list:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("""
                SELECT ID, USER_ID, TELEGRAM_ID, USERNAME, FIRST_NAME, LAST_NAME,
                       LANGUAGE_CODE, IS_BOT, CREATED_AT
                FROM TELEGRAM_USERS
                ORDER BY CREATED_AT DESC
            """)
            return await cur.fetchall()


async def get_user_by_telegram_id(pool, telegram_id: int) -> dict | None:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM TELEGRAM_USERS WHERE TELEGRAM_ID = %s", (telegram_id,)
            )
            return await cur.fetchone()
