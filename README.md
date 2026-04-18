# 🌾 Agriculture Telegram Bot

Captures Telegram user IDs from groups/DMs and stores them in MySQL (`TELEGRAM_USERS` table).

---
## Project setup
1. Project Directory
```bash
mkdir RITHTHY_TELEGRAM_BOT_SYSTEM
cd RITHTHY_TELEGRAM_BOT_SYSTEM
```
2. Activate venv
```bash
Create env
- python -m venv venv
Activate
- venv/Scripts/Activate # Due to virtual directory for this only project control package in the project only
```
3. Install packages from requirements.txt to venv
```bash
pip install -r requirements.txt
python3 -m pip install -r requirements.txt
```

# Packages installation
pip install python-telegram-bot
pip install aiogram

## FOR MULTI BOT 
pip install -U aiogram

## Run docker
##### build container &image
docker build -t telegram_bot_management .
##### Run docker
docker run --rm telegram_bot_management

### Install Packages
pip install python-docx

----
## Project Structure

```bash
RITHTHY_TELEGRAM_BOT_SYSTEM_1/
├── db/                          # Database layer (schemas, pool, connection logic)
│   ├── __init__.py              # Marks db as a Python package
│   ├── schema.py               # SQL table definitions (users, admins, logs, etc.)
│   └── pool.py                 # Async MySQL connection pool manager
│
├── handlers/                    # Telegram bot command & event handlers
│   ├── __init__.py              # Registers all handlers to bot dispatcher/router
│   ├── user.py                 # User commands (/start, /help, profile, etc.)
│   ├── admin.py               # Admin commands (ban, broadcast, stats, etc.)
│   └── group.py               # Group chat features (moderation, filters, welcome msgs)
│
├── middlewares/                 # Pre-processing layer before handlers execute
│   ├── __init__.py              # Initializes middleware package
│   └── base.py                # Logging, auth checks, rate limits, user validation
│
├── utils/                       # Helper utilities and reusable functions
│   ├── __init__.py              # Marks utils as a package
│   ├── helpers.py             # Formatting, parsing, time, API helpers
│   └── permissions.py         # Role checks (admin/user/owner permissions system)
│
├── main.py                     # 🚀 Entry point (starts bot, loads everything, runs polling/webhook)
├── bot.py                      # 🤖 Bot factory (creates bot + dispatcher, config injection)
├── db.py                       # ⚡ High-level DB query functions (fetch/execute wrappers)
│
├── requirements.txt            # Python dependencies list (aiogram, asyncmy, etc.)
├── .env                        # 🔐 Secrets (BOT_TOKEN, DB_PASSWORD, API keys) — NEVER COMMIT
├── Dockerfile                  # 🐳 Container setup for running bot in Docker
└── docker-compose.yml          # 🧩 Multi-service setup (bot + MySQL + networking)
```


---

## ▶️ Run with Python directly

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure `.env`
Edit `.env` with your credentials (already pre-filled).

### 3. Run
```bash
python main.py
```

---

## 🐳 Run with Docker

### Option A — Docker Compose (recommended)
```bash
docker compose up --build -d
```

View logs:
```bash
docker compose logs -f
```

Stop:
```bash
docker compose down
```

### Option B — Plain Docker
```bash
docker build -t agriculture-bot .
docker run -d --name agriculture-bot --env-file .env agriculture-bot
```
pip install python-dotenv
---

## 💬 Bot Commands

| Command    | Description                              |
|-----------|------------------------------------------|
| `/start`  | Register yourself, get your USER_ID      |
| `/myid`   | Show your USER_ID & Telegram ID          |
| `/whoami` | Full profile from the database           |
| `/id`     | Show current chat/group ID               |
| `/users`  | List all registered users                |
| `/help`   | Show all commands                        |

---

## 🗃️ Database Flow

1. On first contact → inserts a row into `USERS` table, gets an auto-increment `USER_ID`
2. Inserts into `TELEGRAM_USERS` linking `USER_ID ↔ TELEGRAM_ID`
3. Subsequent contacts → updates username/name fields only
4. Works in **private chats**, **groups**, and captures **new members** joining a group automatically

---

## ⚙️ Auto-capture

Every message sent in any chat where the bot is present automatically saves that user to the DB — no command needed.


docker compose up --build -d
docker compose logs -f   # watch logs


## MySQL
```bash
CREATE TABLE TELEGRAM_USERS (
    ID BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    TELEGRAM_USER_ID BIGINT UNSIGNED NOT NULL UNIQUE,
    USERNAME VARCHAR(255) NULL,
    FIRST_NAME VARCHAR(255) NULL,
    LAST_NAME VARCHAR(255) NULL,
    FULL_NAME VARCHAR(255) NULL,
    PHONE VARCHAR(30) NULL,
    EMAIL VARCHAR(255) NULL,
    LANGUAGE_CODE VARCHAR(20) NULL,
    COUNTRY_CODE VARCHAR(10) NULL,
    TIMEZONE VARCHAR(100) NULL,
    PROFILE_PHOTO_URL TEXT NULL,

    IS_BOT BOOLEAN DEFAULT FALSE,
    IS_PREMIUM BOOLEAN DEFAULT FALSE,
    IS_ACTIVE BOOLEAN DEFAULT TRUE,
    IS_BLOCKED BOOLEAN DEFAULT FALSE,
    IS_BANNED BOOLEAN DEFAULT FALSE,
    BAN_REASON VARCHAR(255) NULL,

    REFERRAL_CODE VARCHAR(100) NULL UNIQUE,
    REFERRED_BY_USER_ID BIGINT UNSIGNED NULL,

    TOTAL_COMMANDS INT UNSIGNED DEFAULT 0,
    TOTAL_MESSAGES INT UNSIGNED DEFAULT 0,

    LAST_SEEN_AT TIMESTAMP NULL,
    LAST_COMMAND_AT TIMESTAMP NULL,
    LAST_MESSAGE_AT TIMESTAMP NULL,

    CREATED_AT TIMESTAMP NULL,
    UPDATED_AT TIMESTAMP NULL,
    DELETED_AT TIMESTAMP NULL,

    CONSTRAINT FK_TU_REFERRAL
        FOREIGN KEY (REFERRED_BY_USER_ID)
        REFERENCES TELEGRAM_USERS(ID)
        ON DELETE SET NULL
);

CREATE TABLE CHATS (
    ID BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    TELEGRAM_CHAT_ID BIGINT NOT NULL UNIQUE,
    CHAT_TYPE VARCHAR(50) NOT NULL,
    TITLE VARCHAR(255) NULL,
    USERNAME VARCHAR(255) NULL,
    DESCRIPTION TEXT NULL,

    IS_ACTIVE BOOLEAN DEFAULT TRUE,
    IS_ARCHIVED BOOLEAN DEFAULT FALSE,

    MEMBER_COUNT INT UNSIGNED DEFAULT 0,

    CREATED_BY_USER_ID BIGINT UNSIGNED NULL,

    CREATED_AT TIMESTAMP NULL,
    UPDATED_AT TIMESTAMP NULL,

    CONSTRAINT FK_CHATS_USER
        FOREIGN KEY (CREATED_BY_USER_ID)
        REFERENCES TELEGRAM_USERS(ID)
        ON DELETE SET NULL
);

CREATE TABLE COMMANDS (
    ID BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    COMMAND_NAME VARCHAR(100) NOT NULL UNIQUE,
    DESCRIPTION VARCHAR(255) NULL,
    CATEGORY VARCHAR(100) NULL,

    IS_ACTIVE BOOLEAN DEFAULT TRUE,
    REQUIRES_ADMIN BOOLEAN DEFAULT FALSE,
    RATE_LIMIT_SECONDS INT UNSIGNED DEFAULT 0,
    SORT_ORDER INT DEFAULT 0,

    CREATED_AT TIMESTAMP NULL,
    UPDATED_AT TIMESTAMP NULL
);

CREATE TABLE USER_COMMAND_LOGS (
    ID BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    USER_ID BIGINT UNSIGNED NOT NULL,
    CHAT_ID BIGINT UNSIGNED NOT NULL,
    COMMAND_ID BIGINT UNSIGNED NOT NULL,

    MESSAGE_ID BIGINT NULL,
    REPLY_TO_MESSAGE_ID BIGINT NULL,
    MESSAGE_TEXT TEXT NULL,

    PLATFORM VARCHAR(50) NULL,
    DEVICE_TYPE VARCHAR(50) NULL,

    STATUS VARCHAR(50) DEFAULT 'SUCCESS',
    ERROR_MESSAGE TEXT NULL,

    EXECUTION_MS INT UNSIGNED DEFAULT 0,

    SENT_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CREATED_AT TIMESTAMP NULL,
    UPDATED_AT TIMESTAMP NULL,

    CONSTRAINT FK_UCL_USER
        FOREIGN KEY (USER_ID)
        REFERENCES TELEGRAM_USERS(ID)
        ON DELETE CASCADE,

    CONSTRAINT FK_UCL_CHAT
        FOREIGN KEY (CHAT_ID)
        REFERENCES CHATS(ID)
        ON DELETE CASCADE,

    CONSTRAINT FK_UCL_COMMAND
        FOREIGN KEY (COMMAND_ID)
        REFERENCES COMMANDS(ID)
        ON DELETE CASCADE
);

CREATE TABLE OUTGOING_MESSAGES (
    ID BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    USER_ID BIGINT UNSIGNED NOT NULL,
    CHAT_ID BIGINT UNSIGNED NOT NULL,

    MESSAGE_TYPE VARCHAR(50) DEFAULT 'TEXT',
    MESSAGE_TEXT TEXT NULL,
    MEDIA_URL TEXT NULL,
    BUTTON_JSON JSON NULL,

    TELEGRAM_MESSAGE_ID BIGINT NULL,

    STATUS VARCHAR(50) DEFAULT 'PENDING',
    FAILED_REASON TEXT NULL,
    RETRY_COUNT INT UNSIGNED DEFAULT 0,

    SENT_AT TIMESTAMP NULL,
    DELIVERED_AT TIMESTAMP NULL,
    READ_AT TIMESTAMP NULL,

    CREATED_AT TIMESTAMP NULL,
    UPDATED_AT TIMESTAMP NULL,

    CONSTRAINT FK_OM_USER
        FOREIGN KEY (USER_ID)
        REFERENCES TELEGRAM_USERS(ID)
        ON DELETE CASCADE,

    CONSTRAINT FK_OM_CHAT
        FOREIGN KEY (CHAT_ID)
        REFERENCES CHATS(ID)
        ON DELETE CASCADE
);
CREATE TABLE TELEGRAM_USERS (
    ID BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    TELEGRAM_USER_ID BIGINT UNSIGNED NOT NULL UNIQUE,
    USERNAME VARCHAR(255) NULL,
    FIRST_NAME VARCHAR(255) NULL,
    LAST_NAME VARCHAR(255) NULL,
    FULL_NAME VARCHAR(255) NULL,
    PHONE VARCHAR(30) NULL,
    EMAIL VARCHAR(255) NULL,
    LANGUAGE_CODE VARCHAR(20) NULL,
    COUNTRY_CODE VARCHAR(10) NULL,
    TIMEZONE VARCHAR(100) NULL,
    PROFILE_PHOTO_URL TEXT NULL,

    IS_BOT BOOLEAN DEFAULT FALSE,
    IS_PREMIUM BOOLEAN DEFAULT FALSE,
    IS_ACTIVE BOOLEAN DEFAULT TRUE,
    IS_BLOCKED BOOLEAN DEFAULT FALSE,
    IS_BANNED BOOLEAN DEFAULT FALSE,
    BAN_REASON VARCHAR(255) NULL,

    REFERRAL_CODE VARCHAR(100) NULL UNIQUE,
    REFERRED_BY_USER_ID BIGINT UNSIGNED NULL,

    TOTAL_COMMANDS INT UNSIGNED DEFAULT 0,
    TOTAL_MESSAGES INT UNSIGNED DEFAULT 0,

    LAST_SEEN_AT TIMESTAMP NULL,
    LAST_COMMAND_AT TIMESTAMP NULL,
    LAST_MESSAGE_AT TIMESTAMP NULL,

    CREATED_AT TIMESTAMP NULL,
    UPDATED_AT TIMESTAMP NULL,
    DELETED_AT TIMESTAMP NULL,

    CONSTRAINT FK_TU_REFERRAL
        FOREIGN KEY (REFERRED_BY_USER_ID)
        REFERENCES TELEGRAM_USERS(ID)
        ON DELETE SET NULL
);

CREATE TABLE CHATS (
    ID BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    TELEGRAM_CHAT_ID BIGINT NOT NULL UNIQUE,
    CHAT_TYPE VARCHAR(50) NOT NULL,
    TITLE VARCHAR(255) NULL,
    USERNAME VARCHAR(255) NULL,
    DESCRIPTION TEXT NULL,

    IS_ACTIVE BOOLEAN DEFAULT TRUE,
    IS_ARCHIVED BOOLEAN DEFAULT FALSE,

    MEMBER_COUNT INT UNSIGNED DEFAULT 0,

    CREATED_BY_USER_ID BIGINT UNSIGNED NULL,

    CREATED_AT TIMESTAMP NULL,
    UPDATED_AT TIMESTAMP NULL,

    CONSTRAINT FK_CHATS_USER
        FOREIGN KEY (CREATED_BY_USER_ID)
        REFERENCES TELEGRAM_USERS(ID)
        ON DELETE SET NULL
);

CREATE TABLE COMMANDS (
    ID BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    COMMAND_NAME VARCHAR(100) NOT NULL UNIQUE,
    DESCRIPTION VARCHAR(255) NULL,
    CATEGORY VARCHAR(100) NULL,

    IS_ACTIVE BOOLEAN DEFAULT TRUE,
    REQUIRES_ADMIN BOOLEAN DEFAULT FALSE,
    RATE_LIMIT_SECONDS INT UNSIGNED DEFAULT 0,
    SORT_ORDER INT DEFAULT 0,

    CREATED_AT TIMESTAMP NULL,
    UPDATED_AT TIMESTAMP NULL
);

CREATE TABLE USER_COMMAND_LOGS (
    ID BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    USER_ID BIGINT UNSIGNED NOT NULL,
    CHAT_ID BIGINT UNSIGNED NOT NULL,
    COMMAND_ID BIGINT UNSIGNED NOT NULL,

    MESSAGE_ID BIGINT NULL,
    REPLY_TO_MESSAGE_ID BIGINT NULL,
    MESSAGE_TEXT TEXT NULL,

    PLATFORM VARCHAR(50) NULL,
    DEVICE_TYPE VARCHAR(50) NULL,

    STATUS VARCHAR(50) DEFAULT 'SUCCESS',
    ERROR_MESSAGE TEXT NULL,

    EXECUTION_MS INT UNSIGNED DEFAULT 0,

    SENT_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CREATED_AT TIMESTAMP NULL,
    UPDATED_AT TIMESTAMP NULL,

    CONSTRAINT FK_UCL_USER
        FOREIGN KEY (USER_ID)
        REFERENCES TELEGRAM_USERS(ID)
        ON DELETE CASCADE,

    CONSTRAINT FK_UCL_CHAT
        FOREIGN KEY (CHAT_ID)
        REFERENCES CHATS(ID)
        ON DELETE CASCADE,

    CONSTRAINT FK_UCL_COMMAND
        FOREIGN KEY (COMMAND_ID)
        REFERENCES COMMANDS(ID)
        ON DELETE CASCADE
);

CREATE TABLE OUTGOING_MESSAGES (
    ID BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    USER_ID BIGINT UNSIGNED NOT NULL,
    CHAT_ID BIGINT UNSIGNED NOT NULL,

    MESSAGE_TYPE VARCHAR(50) DEFAULT 'TEXT',
    MESSAGE_TEXT TEXT NULL,
    MEDIA_URL TEXT NULL,
    BUTTON_JSON JSON NULL,

    TELEGRAM_MESSAGE_ID BIGINT NULL,

    STATUS VARCHAR(50) DEFAULT 'PENDING',
    FAILED_REASON TEXT NULL,
    RETRY_COUNT INT UNSIGNED DEFAULT 0,

    SENT_AT TIMESTAMP NULL,
    DELIVERED_AT TIMESTAMP NULL,
    READ_AT TIMESTAMP NULL,

    CREATED_AT TIMESTAMP NULL,
    UPDATED_AT TIMESTAMP NULL,

    CONSTRAINT FK_OM_USER
        FOREIGN KEY (USER_ID)
        REFERENCES TELEGRAM_USERS(ID)
        ON DELETE CASCADE,

    CONSTRAINT FK_OM_CHAT
        FOREIGN KEY (CHAT_ID)
        REFERENCES CHATS(ID)
        ON DELETE CASCADE
);
```

## SSL
```Why SSL is needed

SSL (technically TLS) encrypts the connection between your app and the database.

Simple rule
Local dev → ❌ no SSL
Remote/cloud DB → ✅ use SSL
```