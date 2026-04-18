"""handlers/user.py — Public commands."""

import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType

import db
from utils.helpers import display_name, fmt_user, gender_keyboard

logger = logging.getLogger(__name__)
router = Router()


# ── /start ────────────────────────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, pool, db_user: dict, **_):
    status = "✅ Registered" if db_user["is_new"] else "🔄 Welcome back"
    rec = await db.get_user_by_telegram_id(pool, message.from_user.id)
    name = display_name(message.from_user)

    await message.answer(
        f"👋 Hello, <b>{name}</b>!\n\n"
        f"{status} in the system.\n\n"
        f"🗄 <b>System ID:</b> <code>{rec['ID']}</code>\n"
        f"📱 <b>Telegram ID:</b> <code>{rec['TELEGRAM_USER_ID']}</code>\n\n"
        f"Use /menu to explore features or /help for commands."
    )


# ── /help ─────────────────────────────────────────────────────────────────────
@router.message(Command("help"))
async def cmd_help(message: Message, pool, db_user: dict, **_):
    is_admin = db_user.get("admin_level", 0) > 0
    cmds = await db.get_active_commands(pool, admin=is_admin)

    categories: dict[str, list] = {}
    for c in cmds:
        cat = c["CATEGORY"] or "general"
        categories.setdefault(cat, []).append(c)

    cat_icons = {
        "general": "🏠", "account": "👤", "subscription": "💳",
        "info": "ℹ️", "support": "🆘", "admin": "🛡️",
    }

    lines = ["🤖 <b>Available Commands</b>\n"]
    for cat, items in categories.items():
        if cat == "admin" and not is_admin:
            continue
        icon = cat_icons.get(cat, "📌")
        lines.append(f"\n{icon} <b>{cat.title()}</b>")
        for c in items:
            lines.append(f"  /{c['COMMAND_NAME']} — {c['DESCRIPTION'] or ''}")

    await message.answer("\n".join(lines))


# ── /menu ─────────────────────────────────────────────────────────────────────
@router.message(Command("menu"))
async def cmd_menu(message: Message, **_):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Profile",    callback_data="menu_profile"),
         InlineKeyboardButton(text="⚙️ Settings",   callback_data="menu_settings")],
        [InlineKeyboardButton(text="📊 My Stats",   callback_data="menu_stats"),
         InlineKeyboardButton(text="📋 History",    callback_data="menu_history")],
        [InlineKeyboardButton(text="💳 Subscribe",  callback_data="menu_subscribe"),
         InlineKeyboardButton(text="🆘 Support",    callback_data="menu_support")],
        [InlineKeyboardButton(text="ℹ️ About",      callback_data="menu_about")],
    ])
    await message.answer("📋 <b>Main Menu</b>\n\nChoose an option:", reply_markup=kb)


@router.callback_query(F.data.startswith("menu_"))
async def cb_menu(call: CallbackQuery, pool, **_):
    action = call.data.split("menu_")[1]
    dispatch = {
        "profile":   _send_profile,
        "settings":  _send_settings_hint,
        "stats":     _send_my_stats,
        "history":   _send_history,
        "subscribe": _send_subscribe,
        "support":   _send_support,
        "about":     _send_about,
    }
    fn = dispatch.get(action)
    if fn:
        await fn(call, pool)
    await call.answer()


async def _send_profile(call, pool):
    rec = await db.get_user_by_telegram_id(pool, call.from_user.id)
    await call.message.answer(fmt_user(rec))


async def _send_settings_hint(call, pool):
    await call.message.answer("⚙️ Use /settings to manage your preferences.")


async def _send_my_stats(call, pool):
    rec = await db.get_user_by_telegram_id(pool, call.from_user.id)
    await call.message.answer(
        f"📊 <b>Your Stats</b>\n\n"
        f"Commands used: <b>{rec['TOTAL_COMMANDS']}</b>\n"
        f"Messages sent: <b>{rec['TOTAL_MESSAGES']}</b>\n"
        f"Last seen: <b>{rec['LAST_SEEN_AT']}</b>\n"
        f"Member since: <b>{rec['CREATED_AT']}</b>"
    )


async def _send_history(call, pool):
    rec = await db.get_user_by_telegram_id(pool, call.from_user.id)
    rows = await db.get_user_history(pool, rec["ID"], limit=8)
    if not rows:
        await call.message.answer("No command history yet.")
        return
    lines = [f"📋 <b>Recent Commands</b>\n"]
    for r in rows:
        lines.append(f"/{r['COMMAND_NAME']} — {r['STATUS']} — {str(r['SENT_AT'])[:16]}")
    await call.message.answer("\n".join(lines))


async def _send_subscribe(call, pool):
    await call.message.answer("💳 Use /subscribe to view available plans.")


async def _send_support(call, pool):
    contact = await db.get_setting(pool, "SUPPORT_USERNAME", "")
    text = f"🆘 <b>Support</b>\n\n"
    text += f"Contact: @{contact}" if contact else "Please use /support to reach us."
    await call.message.answer(text)


async def _send_about(call, pool):
    about = await db.get_setting(pool, "ABOUT_TEXT", "🤖 Bot")
    await call.message.answer(about)


# ── /profile ──────────────────────────────────────────────────────────────────
@router.message(Command("profile"))
async def cmd_profile(message: Message, pool, **_):
    rec = await db.get_user_by_telegram_id(pool, message.from_user.id)
    gender = (rec.get("GENDER") or "Not set").title()
    premium = "⭐ Yes" if rec.get("IS_PREMIUM") else "No"
    ref = rec.get("REFERRAL_CODE") or "—"

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🚻 Set Gender", callback_data="set_gender"),
    ]])
    await message.answer(
        f"👤 <b>Your Profile</b>\n\n"
        f"Name: <b>{rec.get('FULL_NAME') or '—'}</b>\n"
        f"Username: {'@' + rec['USERNAME'] if rec.get('USERNAME') else '—'}\n"
        f"Gender: <b>{gender}</b>\n"
        f"Language: <b>{rec.get('LANGUAGE_CODE') or '—'}</b>\n"
        f"Premium: <b>{premium}</b>\n"
        f"Referral Code: <code>{ref}</code>\n\n"
        f"🗄 System ID: <code>{rec['ID']}</code>\n"
        f"📱 Telegram ID: <code>{rec['TELEGRAM_USER_ID']}</code>\n"
        f"📅 Joined: {str(rec['CREATED_AT'])[:10]}",
        reply_markup=kb,
    )


@router.callback_query(F.data == "set_gender")
async def cb_set_gender(call: CallbackQuery, **_):
    await call.message.answer("🚻 <b>Select your gender:</b>", reply_markup=gender_keyboard())
    await call.answer()


@router.callback_query(F.data.startswith("gender_"))
async def cb_gender_chosen(call: CallbackQuery, pool, **_):
    gender = call.data.split("gender_")[1]
    await db.set_user_gender(pool, call.from_user.id, gender)
    icon = {"male": "♂️", "female": "♀️", "other": "⚧️"}.get(gender, "")
    await call.message.edit_text(f"✅ Gender set to <b>{gender.title()}</b> {icon}")
    await call.answer()


# ── /settings ─────────────────────────────────────────────────────────────────
@router.message(Command("settings"))
async def cmd_settings(message: Message, pool, **_):
    rec = await db.get_user_by_telegram_id(pool, message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚻 Set Gender",   callback_data="set_gender")],
        [InlineKeyboardButton(text="🌐 Language",     callback_data="menu_lang")],
    ])
    await message.answer(
        f"⚙️ <b>Settings</b>\n\n"
        f"Language: <b>{rec.get('LANGUAGE_CODE') or '—'}</b>\n"
        f"Gender: <b>{(rec.get('GENDER') or 'Not set').title()}</b>",
        reply_markup=kb,
    )


# ── /language ─────────────────────────────────────────────────────────────────
@router.message(Command("language"))
async def cmd_language(message: Message, **_):
    await message.answer("🌐 Language switching coming soon. Your current language is detected automatically.")


# ── /showmyid ─────────────────────────────────────────────────────────────────
@router.message(Command("showmyid"))
async def cmd_showmyid(message: Message, pool, **_):
    user = message.from_user
    rec = await db.get_user_by_telegram_id(pool, user.id)
    name = display_name(user)
    username_line = f"@{user.username}" if user.username else "—"

    msg = (
        f"╔══════════════════════════════╗\n"
        f"║   🪪  <b>USER IDENTITY CARD</b>   ║\n"
        f"╚══════════════════════════════╝\n\n"
        f"👤 <b>Name:</b> {name}\n"
        f"🔖 <b>Username:</b> {username_line}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗄  <b>System USER_ID</b>\n    <code>{rec['ID']}</code>\n\n"
        f"📱  <b>Telegram ID</b>\n    <code>{rec['TELEGRAM_USER_ID']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗  <b>How to use these IDs</b>\n\n"
        f"<b>1️⃣ Link in app</b>\n"
        f"    Profile → Connect Telegram → enter USER_ID: <code>{rec['ID']}</code>\n\n"
        f"<b>2️⃣ API / message targeting</b>\n"
        f"    Use Telegram ID: <code>{rec['TELEGRAM_USER_ID']}</code>\n\n"
        f"<b>3️⃣ Migration / data import</b>\n"
        f"    <code>user_id={rec['ID']}</code>\n"
        f"    <code>telegram_id={rec['TELEGRAM_USER_ID']}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>Tap any ID to copy. Keep these private.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📋 USER_ID: {rec['ID']}",
                              callback_data=f"copy_uid_{rec['ID']}")],
        [InlineKeyboardButton(text=f"📱 Telegram ID: {rec['TELEGRAM_USER_ID']}",
                              callback_data=f"copy_tid_{rec['TELEGRAM_USER_ID']}")],
    ])
    await message.answer(msg, reply_markup=kb)

    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        try:
            await message.bot.send_message(
                user.id,
                f"🔒 <b>Private copy</b>\n\n"
                f"USER_ID: <code>{rec['ID']}</code>\n"
                f"Telegram ID: <code>{rec['TELEGRAM_USER_ID']}</code>"
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("copy_uid_"))
async def cb_copy_uid(call: CallbackQuery, **_):
    uid = call.data.split("copy_uid_")[1]
    await call.answer(f"USER_ID: {uid}", show_alert=True)


@router.callback_query(F.data.startswith("copy_tid_"))
async def cb_copy_tid(call: CallbackQuery, **_):
    tid = call.data.split("copy_tid_")[1]
    await call.answer(f"Telegram ID: {tid}", show_alert=True)


# ── /myid ─────────────────────────────────────────────────────────────────────
@router.message(Command("myid"))
async def cmd_myid(message: Message, pool, **_):
    rec = await db.get_user_by_telegram_id(pool, message.from_user.id)
    await message.answer(
        f"🆔 <b>Your IDs</b>\n\n"
        f"🗄 System USER_ID: <code>{rec['ID']}</code>\n"
        f"📱 Telegram ID: <code>{rec['TELEGRAM_USER_ID']}</code>"
    )


# ── /whoami ───────────────────────────────────────────────────────────────────
@router.message(Command("whoami"))
async def cmd_whoami(message: Message, pool, **_):
    rec = await db.get_user_by_telegram_id(pool, message.from_user.id)
    await message.answer(fmt_user(rec))


# ── /id ───────────────────────────────────────────────────────────────────────
@router.message(Command("id"))
async def cmd_id(message: Message, **_):
    chat = message.chat
    user = message.from_user
    await message.answer(
        f"ℹ️ <b>Chat Info</b>\n"
        f"Chat ID: <code>{chat.id}</code>\n"
        f"Type: {chat.type}\n"
        f"Title: {getattr(chat, 'title', '—') or '—'}\n\n"
        f"👤 <b>Your Info</b>\n"
        f"Telegram ID: <code>{user.id}</code>\n"
        f"Username: {'@' + user.username if user.username else '—'}"
    )


# ── /status ───────────────────────────────────────────────────────────────────
@router.message(Command("status"))
async def cmd_status(message: Message, pool, **_):
    rec = await db.get_user_by_telegram_id(pool, message.from_user.id)
    active = "✅ Active" if rec.get("IS_ACTIVE") else "⛔ Inactive"
    banned = "🚫 Banned" if rec.get("IS_BANNED") else "✅ Clean"
    await message.answer(
        f"📊 <b>Account Status</b>\n\n"
        f"Status: {active}\n"
        f"Ban status: {banned}\n"
        f"Commands: <b>{rec['TOTAL_COMMANDS']}</b>\n"
        f"Last active: {str(rec.get('LAST_SEEN_AT') or '—')[:16]}"
    )


# ── /history ──────────────────────────────────────────────────────────────────
@router.message(Command("history"))
async def cmd_history(message: Message, pool, **_):
    rec = await db.get_user_by_telegram_id(pool, message.from_user.id)
    rows = await db.get_user_history(pool, rec["ID"])
    if not rows:
        await message.answer("No history yet. Start using commands!")
        return
    lines = ["📋 <b>Your Recent Commands</b>\n"]
    for r in rows:
        lines.append(f"/{r['COMMAND_NAME']}  •  {r['STATUS']}  •  {str(r['SENT_AT'])[:16]}")
    await message.answer("\n".join(lines))


# ── /search ───────────────────────────────────────────────────────────────────
@router.message(Command("search"))
async def cmd_search(message: Message, pool, **_):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /search <username or telegram_id>")
        return
    query = parts[1].lstrip("@")
    # Try as integer (telegram_id)
    rec = None
    if query.isdigit():
        rec = await db.get_user_by_telegram_id(pool, int(query))
    if not rec:
        # search by username
        async with pool.acquire() as conn:
            import aiomysql
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT * FROM TELEGRAM_USERS WHERE USERNAME=%s LIMIT 1", (query,)
                )
                rec = await cur.fetchone()
    if not rec:
        await message.answer("❌ User not found.")
        return
    await message.answer(fmt_user(rec))


# ── /subscribe / /unsubscribe ─────────────────────────────────────────────────
@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message, **_):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥉 Basic — Free",    callback_data="plan_basic")],
        [InlineKeyboardButton(text="🥈 Pro — $9.99/mo",  callback_data="plan_pro")],
        [InlineKeyboardButton(text="🥇 Elite — $29/mo",  callback_data="plan_elite")],
    ])
    await message.answer("💳 <b>Choose a Plan</b>", reply_markup=kb)


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: Message, **_):
    await message.answer("❌ Subscription cancellation coming soon. Contact /support.")


# ── /support / /feedback / /about / /contact ─────────────────────────────────
@router.message(Command("support"))
async def cmd_support(message: Message, pool, **_):
    username = await db.get_setting(pool, "SUPPORT_USERNAME", "")
    info = await db.get_setting(pool, "CONTACT_INFO", "")
    text = "🆘 <b>Support</b>\n\n"
    if username:
        text += f"👤 @{username}\n"
    if info:
        text += info
    await message.answer(text)


@router.message(Command("feedback"))
async def cmd_feedback(message: Message, **_):
    await message.answer("📝 Send us your feedback by replying to this message (coming soon).")


@router.message(Command("about"))
async def cmd_about(message: Message, pool, **_):
    text = await db.get_setting(pool, "ABOUT_TEXT", "🤖 Agriculture Bot")
    await message.answer(text)


@router.message(Command("contact"))
async def cmd_contact(message: Message, pool, **_):
    text = await db.get_setting(pool, "CONTACT_INFO", "📬 contact@example.com")
    await message.answer(f"📬 <b>Contact</b>\n\n{text}")
