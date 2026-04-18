"""
db/schema.py  –  All CREATE TABLE statements (idempotent).
Run once on startup via db.init_schema(pool).
"""

SCHEMA_SQL = """
-- ── Core user table ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS TELEGRAM_USERS (
    ID                   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    TELEGRAM_USER_ID     BIGINT UNSIGNED NOT NULL UNIQUE,
    USERNAME             VARCHAR(255)  NULL,
    FIRST_NAME           VARCHAR(255)  NULL,
    LAST_NAME            VARCHAR(255)  NULL,
    FULL_NAME            VARCHAR(255)  NULL,
    PHONE                VARCHAR(30)   NULL,
    EMAIL                VARCHAR(255)  NULL,
    LANGUAGE_CODE        VARCHAR(20)   NULL,
    COUNTRY_CODE         VARCHAR(10)   NULL,
    TIMEZONE             VARCHAR(100)  NULL,
    PROFILE_PHOTO_URL    TEXT          NULL,
    GENDER               VARCHAR(20)   NULL,   -- male / female / other / NULL
    IS_BOT               BOOLEAN       DEFAULT FALSE,
    IS_PREMIUM           BOOLEAN       DEFAULT FALSE,
    IS_ACTIVE            BOOLEAN       DEFAULT TRUE,
    IS_BLOCKED           BOOLEAN       DEFAULT FALSE,
    IS_BANNED            BOOLEAN       DEFAULT FALSE,
    BAN_REASON           VARCHAR(255)  NULL,
    IS_ADMIN             BOOLEAN       DEFAULT FALSE,
    ADMIN_LEVEL          TINYINT       DEFAULT 0,  -- 0=user 1=mod 2=admin 3=superadmin
    REFERRAL_CODE        VARCHAR(100)  NULL UNIQUE,
    REFERRED_BY_USER_ID  BIGINT UNSIGNED NULL,
    TOTAL_COMMANDS       INT UNSIGNED  DEFAULT 0,
    TOTAL_MESSAGES       INT UNSIGNED  DEFAULT 0,
    LAST_SEEN_AT         TIMESTAMP     NULL,
    LAST_COMMAND_AT      TIMESTAMP     NULL,
    LAST_MESSAGE_AT      TIMESTAMP     NULL,
    CREATED_AT           TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT           TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    DELETED_AT           TIMESTAMP     NULL,
    CONSTRAINT FK_TU_REFERRAL
        FOREIGN KEY (REFERRED_BY_USER_ID)
        REFERENCES TELEGRAM_USERS(ID)
        ON DELETE SET NULL
);

-- ── Chats / Groups ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS CHATS (
    ID                   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    TELEGRAM_CHAT_ID     BIGINT NOT NULL UNIQUE,
    CHAT_TYPE            VARCHAR(50)   NOT NULL,
    TITLE                VARCHAR(255)  NULL,
    USERNAME             VARCHAR(255)  NULL,
    DESCRIPTION          TEXT          NULL,
    IS_ACTIVE            BOOLEAN       DEFAULT TRUE,
    IS_ARCHIVED          BOOLEAN       DEFAULT FALSE,
    IS_LOG_GROUP         BOOLEAN       DEFAULT FALSE,  -- designated admin log group
    IS_MAIN_GROUP        BOOLEAN       DEFAULT FALSE,  -- main public group
    MEMBER_COUNT         INT UNSIGNED  DEFAULT 0,
    CREATED_BY_USER_ID   BIGINT UNSIGNED NULL,
    CREATED_AT           TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT           TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT FK_CHATS_USER
        FOREIGN KEY (CREATED_BY_USER_ID)
        REFERENCES TELEGRAM_USERS(ID)
        ON DELETE SET NULL
);

-- ── Dynamic command registry ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS COMMANDS (
    ID                   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    COMMAND_NAME         VARCHAR(100)  NOT NULL UNIQUE,
    DESCRIPTION          VARCHAR(255)  NULL,
    CATEGORY             VARCHAR(100)  NULL,
    IS_ACTIVE            BOOLEAN       DEFAULT TRUE,
    REQUIRES_ADMIN       BOOLEAN       DEFAULT FALSE,
    RATE_LIMIT_SECONDS   INT UNSIGNED  DEFAULT 0,
    SORT_ORDER           INT           DEFAULT 0,
    CREATED_AT           TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT           TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ── Bot settings (key-value store) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS BOT_SETTINGS (
    ID           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    SETTING_KEY  VARCHAR(100) NOT NULL UNIQUE,
    SETTING_VALUE TEXT        NULL,
    DESCRIPTION  VARCHAR(255) NULL,
    UPDATED_BY   BIGINT UNSIGNED NULL,
    CREATED_AT   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ── User command logs ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS USER_COMMAND_LOGS (
    ID                   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    USER_ID              BIGINT UNSIGNED NOT NULL,
    CHAT_ID              BIGINT UNSIGNED NOT NULL,
    COMMAND_ID           BIGINT UNSIGNED NOT NULL,
    MESSAGE_ID           BIGINT         NULL,
    REPLY_TO_MESSAGE_ID  BIGINT         NULL,
    MESSAGE_TEXT         TEXT           NULL,
    PLATFORM             VARCHAR(50)    NULL,
    DEVICE_TYPE          VARCHAR(50)    NULL,
    STATUS               VARCHAR(50)    DEFAULT 'SUCCESS',
    ERROR_MESSAGE        TEXT           NULL,
    EXECUTION_MS         INT UNSIGNED   DEFAULT 0,
    SENT_AT              TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    CREATED_AT           TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT           TIMESTAMP      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT FK_UCL_USER    FOREIGN KEY (USER_ID)    REFERENCES TELEGRAM_USERS(ID) ON DELETE CASCADE,
    CONSTRAINT FK_UCL_CHAT    FOREIGN KEY (CHAT_ID)    REFERENCES CHATS(ID)          ON DELETE CASCADE,
    CONSTRAINT FK_UCL_COMMAND FOREIGN KEY (COMMAND_ID) REFERENCES COMMANDS(ID)       ON DELETE CASCADE
);

-- ── Outgoing messages ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS OUTGOING_MESSAGES (
    ID                   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    USER_ID              BIGINT UNSIGNED NOT NULL,
    CHAT_ID              BIGINT UNSIGNED NOT NULL,
    MESSAGE_TYPE         VARCHAR(50)    DEFAULT 'TEXT',
    MESSAGE_TEXT         TEXT           NULL,
    MEDIA_URL            TEXT           NULL,
    BUTTON_JSON          JSON           NULL,
    TELEGRAM_MESSAGE_ID  BIGINT         NULL,
    STATUS               VARCHAR(50)    DEFAULT 'PENDING',
    FAILED_REASON        TEXT           NULL,
    RETRY_COUNT          INT UNSIGNED   DEFAULT 0,
    SENT_AT              TIMESTAMP      NULL,
    DELIVERED_AT         TIMESTAMP      NULL,
    READ_AT              TIMESTAMP      NULL,
    CREATED_AT           TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT           TIMESTAMP      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT FK_OM_USER FOREIGN KEY (USER_ID) REFERENCES TELEGRAM_USERS(ID) ON DELETE CASCADE,
    CONSTRAINT FK_OM_CHAT FOREIGN KEY (CHAT_ID) REFERENCES CHATS(ID)          ON DELETE CASCADE
);

-- ── Raw update log ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS TELEGRAM_UPDATES (
    ID            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    UPDATE_ID     BIGINT NOT NULL UNIQUE,
    USER_ID       BIGINT UNSIGNED NULL,
    CHAT_ID       BIGINT UNSIGNED NULL,
    UPDATE_TYPE   VARCHAR(100)   NULL,
    RAW_JSON      JSON           NOT NULL,
    PROCESSED     BOOLEAN        DEFAULT FALSE,
    PROCESSED_AT  TIMESTAMP      NULL,
    ERROR_MESSAGE TEXT           NULL,
    RECEIVED_AT   TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    CREATED_AT    TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT    TIMESTAMP      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT FK_TUP_USER FOREIGN KEY (USER_ID) REFERENCES TELEGRAM_USERS(ID) ON DELETE SET NULL,
    CONSTRAINT FK_TUP_CHAT FOREIGN KEY (CHAT_ID) REFERENCES CHATS(ID)          ON DELETE SET NULL
);

-- ── User sessions (FSM state persistence) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS USER_SESSIONS (
    ID            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    USER_ID       BIGINT UNSIGNED NOT NULL UNIQUE,
    CURRENT_STEP  VARCHAR(100)   NULL,
    STATE_JSON    JSON           NULL,
    EXPIRES_AT    TIMESTAMP      NULL,
    CREATED_AT    TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT    TIMESTAMP      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT FK_US_USER FOREIGN KEY (USER_ID) REFERENCES TELEGRAM_USERS(ID) ON DELETE CASCADE
);

-- ── Broadcasts ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS BROADCASTS (
    ID            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    TITLE         VARCHAR(255)   NOT NULL,
    MESSAGE_TEXT  TEXT           NOT NULL,
    MEDIA_URL     TEXT           NULL,
    TOTAL_USERS   INT UNSIGNED   DEFAULT 0,
    SUCCESS_COUNT INT UNSIGNED   DEFAULT 0,
    FAILED_COUNT  INT UNSIGNED   DEFAULT 0,
    STATUS        VARCHAR(50)    DEFAULT 'DRAFT',
    SCHEDULED_AT  TIMESTAMP      NULL,
    SENT_AT       TIMESTAMP      NULL,
    CREATED_BY    BIGINT UNSIGNED NULL,
    CREATED_AT    TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT    TIMESTAMP      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ── Subscriptions ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS USER_SUBSCRIPTIONS (
    ID          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    USER_ID     BIGINT UNSIGNED NOT NULL,
    PLAN_NAME   VARCHAR(100)   NOT NULL,
    STATUS      VARCHAR(50)    DEFAULT 'ACTIVE',
    START_DATE  DATE           NOT NULL,
    END_DATE    DATE           NULL,
    CREATED_AT  TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT  TIMESTAMP      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT FK_SUB_USER FOREIGN KEY (USER_ID) REFERENCES TELEGRAM_USERS(ID) ON DELETE CASCADE
);

-- ── Payments ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS USER_PAYMENTS (
    ID             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    USER_ID        BIGINT UNSIGNED NOT NULL,
    AMOUNT         DECIMAL(12,2)  NOT NULL,
    CURRENCY       VARCHAR(10)    DEFAULT 'USD',
    PAYMENT_METHOD VARCHAR(50)    NULL,
    TRANSACTION_ID VARCHAR(255)   NULL UNIQUE,
    STATUS         VARCHAR(50)    DEFAULT 'PENDING',
    PAID_AT        TIMESTAMP      NULL,
    CREATED_AT     TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT     TIMESTAMP      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT FK_PAY_USER FOREIGN KEY (USER_ID) REFERENCES TELEGRAM_USERS(ID) ON DELETE CASCADE
);
"""

# ── Default seed data ────────────────────────────────────────────────────────

DEFAULT_COMMANDS = [
    # (name, description, category, requires_admin, sort_order)
    ("start",       "Start / register",                  "general",      False, 1),
    ("help",        "Show help",                         "general",      False, 2),
    ("menu",        "Main menu",                         "general",      False, 3),
    ("profile",     "Your profile",                      "account",      False, 4),
    ("settings",    "User settings",                     "account",      False, 5),
    ("language",    "Change language",                   "account",      False, 6),
    ("showmyid",    "Show your IDs in the group",        "account",      False, 7),
    ("myid",        "Show your IDs privately",           "account",      False, 8),
    ("whoami",      "Full profile from DB",              "account",      False, 9),
    ("subscribe",   "Subscribe to a plan",               "subscription", False, 10),
    ("unsubscribe", "Cancel subscription",               "subscription", False, 11),
    ("status",      "Bot / account status",              "info",         False, 12),
    ("history",     "Your command history",              "info",         False, 13),
    ("search",      "Search users or data",              "info",         False, 14),
    ("support",     "Contact support",                   "support",      False, 15),
    ("feedback",    "Send feedback",                     "support",      False, 16),
    ("about",       "About this bot",                    "info",         False, 17),
    ("contact",     "Contact information",               "info",         False, 18),
    ("id",          "Show chat/group ID",                "info",         False, 19),
    # Admin commands
    ("admin",       "Admin panel",                       "admin",        True,  20),
    ("users",       "List all users",                    "admin",        True,  21),
    ("ban",         "Ban a user",                        "admin",        True,  22),
    ("unban",       "Unban a user",                      "admin",        True,  23),
    ("broadcast",   "Send broadcast message",            "admin",        True,  24),
    ("stats",       "Bot statistics",                    "admin",        True,  25),
    ("report",      "Generate reports",                  "admin",        True,  26),
    ("notify",      "Send notification to user",         "admin",        True,  27),
    ("setwelcome",  "Set welcome message",               "admin",        True,  28),
    ("setwelcome",  "Set welcome message",               "admin",        True,  28),
    ("cmdtoggle",   "Enable/disable a command",          "admin",        True,  29),
    ("setloggroup", "Set log/management group",          "admin",        True,  30),
    ("dashboard",   "Admin dashboard",                   "admin",        True,  31),
    ("export",      "Export user data",                  "admin",        True,  32),
    ("billing",     "Billing overview",                  "admin",        True,  33),
]

DEFAULT_SETTINGS = [
    # (key, value, description)
    ("WELCOME_ENABLED",      "true",  "Enable welcome message on join"),
    ("WELCOME_TEXT",
     "👋 Welcome, {name}! 🎉\n\nYour ID: <code>{telegram_id}</code>\nUSER_ID: <code>{user_id}</code>\n\nType /help to see commands.",
     "Welcome message template. Supports {name}, {telegram_id}, {user_id}, {username}"),
    ("LOG_GROUP_CHAT_ID",    "",      "Telegram chat_id of the management/log group"),
    ("MAIN_GROUP_CHAT_ID",   "",      "Telegram chat_id of the main public group"),
    ("BOT_NAME",             "Agriculture Bot", "Display name of the bot"),
    ("SUPPORT_USERNAME",     "",      "Support contact username (without @)"),
    ("CONTACT_INFO",         "Contact us at support@example.com", "Contact text shown on /contact"),
    ("ABOUT_TEXT",           "🌾 Agriculture Bot — powered by AI.\n\nVersion: 2.0", "About text"),
    ("MAX_BROADCAST_BATCH",  "30",    "Messages per second during broadcast"),
    ("AUTO_LOG_JOINS",       "true",  "Auto-notify log group when user joins"),
]