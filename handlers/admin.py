"""handlers/admin.py — Admin-only commands."""

import logging
import aiomysql
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import db
from utils.helpers import fmt_user, paginate_text

logger = logging.getLogger(__name__)
router = Router()

GENDER_ICONS = {"male": "♂️", "female": "♀️", "other": "⚧️"}


def _is_admin(db_user: dict) -> bool:
    return (db_user or {}).get("admin_level", 0) >= 1


# ── Guard ─────────────────────────────────────────────────────────────────────

async def _guard(message: Message, pool, db_user: dict, level: int = 1) -> bool:
    al = db_user.get("admin_level", 0) if db_user else 0
    if al < level:
        rec = await db.get_user_by_telegram_id(pool, message.from_user.id)
        al = (rec or {}).get("ADMIN_LEVEL") or 0
    if al < level:
        await message.answer("🚫 <b>Access denied.</b> Admins only.")
        return False
    return True


# ── /admin ────────────────────────────────────────────────────────────────────
@router.message(Command("admin"))
async def cmd_admin(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Users",      callback_data="adm_users"),
         InlineKeyboardButton(text="📊 Stats",      callback_data="adm_stats")],
        [InlineKeyboardButton(text="⚙️ Settings",   callback_data="adm_settings"),
         InlineKeyboardButton(text="💬 Commands",   callback_data="adm_commands")],
        [InlineKeyboardButton(text="📢 Broadcast",  callback_data="adm_broadcast_hint"),
         InlineKeyboardButton(text="📤 Export",     callback_data="adm_export")],
    ])
    await message.answer("🛡️ <b>Admin Dashboard</b>", reply_markup=kb)


@router.callback_query(F.data.startswith("adm_"))
async def cb_admin(call: CallbackQuery, pool, db_user: dict = None, **_):
    if not _is_admin(db_user):
        rec = await db.get_user_by_telegram_id(pool, call.from_user.id)
        if not rec or not rec.get("IS_ADMIN"):
            await call.answer("🚫 Admin only", show_alert=True)
            return

    action = call.data[4:]
    await call.answer()

    if action == "stats":
        await _send_stats(call.message, pool)
    elif action == "settings":
        await _send_settings(call.message, pool)
    elif action == "commands":
        await _send_commands_list(call.message, pool)
    elif action == "users":
        await call.message.answer("Use /users to list users.")
    elif action == "broadcast_hint":
        await call.message.answer("Use /broadcast <message> to send a broadcast.")
    elif action == "export":
        await call.message.answer("Use /export to download user data.")


# ── /dashboard ────────────────────────────────────────────────────────────────
@router.message(Command("dashboard"))
async def cmd_dashboard(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user):
        return
    await _send_stats(message, pool)


async def _send_stats(msg: Message, pool):
    s = await db.get_stats(pool)
    u = s["users"] or {}
    top = s.get("top_commands", [])

    gender_line = (
        f"♂️ {u.get('male_count') or 0}  "
        f"♀️ {u.get('female_count') or 0}  "
        f"⚧️ {u.get('other_gender') or 0}  "
        f"❓ {u.get('unknown_gender') or 0}"
    )
    top_str = "\n".join(f"  /{r['COMMAND_NAME']} — {r['uses']}×" for r in top) or "  —"

    await msg.answer(
        f"📊 <b>Bot Statistics</b>\n\n"
        f"👥 <b>Users</b>\n"
        f"  Total:   <b>{u.get('total') or 0}</b>\n"
        f"  Active:  <b>{u.get('active') or 0}</b>\n"
        f"  Banned:  <b>{u.get('banned') or 0}</b>\n"
        f"  Admins:  <b>{u.get('admins') or 0}</b>\n"
        f"  Premium: <b>⭐ {u.get('premium') or 0}</b>\n\n"
        f"🚻 <b>Gender</b>\n  {gender_line}\n\n"
        f"💬 <b>Chats:</b> {s['chats'].get('total') or 0}\n"
        f"📋 <b>Commands logged:</b> {s['commands'].get('total') or 0}\n\n"
        f"🏆 <b>Top Commands</b>\n{top_str}"
    )


async def _send_settings(msg: Message, pool):
    rows = await db.get_all_settings(pool)
    lines = ["⚙️ <b>Bot Settings</b>\n"]
    for r in rows:
        val = str(r["SETTING_VALUE"] or "")
        preview = val[:60] + "…" if len(val) > 60 else val
        lines.append(f"<code>{r['SETTING_KEY']}</code>: {preview}")
    lines.append("\nUse /setsetting KEY VALUE to update.")
    await msg.answer("\n".join(lines))


async def _send_commands_list(msg: Message, pool):
    cmds = await db.get_active_commands(pool, admin=True)
    lines = ["💬 <b>All Commands</b>  (✅=on  ❌=off)\n"]
    for c in cmds:
        icon = "✅" if c["IS_ACTIVE"] else "❌"
        admin = " 🛡️" if c["REQUIRES_ADMIN"] else ""
        lines.append(f"{icon} /{c['COMMAND_NAME']}{admin} — {c['DESCRIPTION'] or ''}")
    lines.append("\nUse /cmdtoggle <name> to toggle.")
    await msg.answer("\n".join(lines))


# ── /stats ────────────────────────────────────────────────────────────────────
@router.message(Command("stats"))
async def cmd_stats(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user):
        return
    await _send_stats(message, pool)


# ── /users ────────────────────────────────────────────────────────────────────
@router.message(Command("users"))
async def cmd_users(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user):
        return
    users = await db.get_all_users(pool, limit=30)
    if not users:
        await message.answer("No users yet.")
        return
    lines = []
    for u in users:
        un = f"@{u['USERNAME']}" if u.get("USERNAME") else "—"
        name = u.get("FULL_NAME") or "—"
        gender = GENDER_ICONS.get((u.get("GENDER") or "").lower(), "❓")
        banned = " 🚫" if u.get("IS_BANNED") else ""
        admin = " 🛡️" if u.get("IS_ADMIN") else ""
        lines.append(
            f"• {gender}{admin}{banned} <b>{name}</b> {un}\n"
            f"  ID <code>{u['TELEGRAM_USER_ID']}</code> · DB <code>{u['ID']}</code>"
        )
    for page in paginate_text(lines, f"👥 <b>Users ({len(users)})</b>"):
        await message.answer(page)


# ── /ban ──────────────────────────────────────────────────────────────────────
@router.message(Command("ban"))
async def cmd_ban(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user, level=2):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Usage: /ban <telegram_id> [reason]")
        return
    tid_str = parts[1]
    reason = parts[2] if len(parts) > 2 else "Admin ban"
    if not tid_str.lstrip("-").isdigit():
        await message.answer("❌ Invalid Telegram ID.")
        return
    tid = int(tid_str)
    ok = await db.ban_user(pool, tid, reason, message.from_user.id)
    if ok:
        await message.answer(f"🚫 User <code>{tid}</code> banned.\nReason: {reason}")
        logger.info(f"Admin {message.from_user.id} banned {tid}: {reason}")
    else:
        await message.answer(f"⚠️ User <code>{tid}</code> not found or already banned.")


# ── /unban ────────────────────────────────────────────────────────────────────
@router.message(Command("unban"))
async def cmd_unban(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user, level=2):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Usage: /unban <telegram_id>")
        return
    tid = int(parts[1])
    ok = await db.unban_user(pool, tid)
    if ok:
        await message.answer(f"✅ User <code>{tid}</code> unbanned.")
    else:
        await message.answer(f"⚠️ User <code>{tid}</code> not found.")


# ── /setadmin ─────────────────────────────────────────────────────────────────
@router.message(Command("setadmin"))
async def cmd_setadmin(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user, level=3):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /setadmin <telegram_id> [level 1-3]")
        return
    tid = int(parts[1])
    level = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 2
    ok = await db.set_admin(pool, tid, level)
    await message.answer(f"{'✅' if ok else '⚠️'} Admin L{level} {'set' if ok else 'failed'} for <code>{tid}</code>.")


# ── /broadcast ────────────────────────────────────────────────────────────────
@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user, level=2):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /broadcast <message text>")
        return
    text = parts[1]

    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT TELEGRAM_USER_ID FROM TELEGRAM_USERS WHERE IS_ACTIVE=1 AND IS_BANNED=0 AND DELETED_AT IS NULL"
            )
            users = await cur.fetchall()

    if not users:
        await message.answer("No active users to broadcast to.")
        return

    status_msg = await message.answer(f"📢 Broadcasting to {len(users)} users…")
    ok, fail = 0, 0
    for u in users:
        try:
            await message.bot.send_message(u["TELEGRAM_USER_ID"], text)
            ok += 1
        except Exception:
            fail += 1

    await status_msg.edit_text(
        f"📢 <b>Broadcast Complete</b>\n\n"
        f"✅ Sent: {ok}\n❌ Failed: {fail}\nTotal: {len(users)}"
    )


# ── /notify ───────────────────────────────────────────────────────────────────
@router.message(Command("notify"))
async def cmd_notify(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /notify <telegram_id> <message>")
        return
    tid, text = parts[1], parts[2]
    if not tid.lstrip("-").isdigit():
        await message.answer("❌ Invalid Telegram ID.")
        return
    try:
        await message.bot.send_message(int(tid), f"🔔 <b>Notification</b>\n\n{text}")
        await message.answer(f"✅ Message sent to <code>{tid}</code>.")
    except Exception as e:
        await message.answer(f"❌ Failed: {e}")


# ── /report ───────────────────────────────────────────────────────────────────
@router.message(Command("report"))
async def cmd_report(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user):
        return
    await _send_stats(message, pool)


# ── /export ───────────────────────────────────────────────────────────────────
@router.message(Command("export"))
async def cmd_export(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user, level=2):
        return
    import io, csv
    from datetime import datetime
    users = await db.get_all_users(pool, limit=10000)
    buf = io.StringIO()
    if users:
        writer = csv.DictWriter(buf, fieldnames=users[0].keys())
        writer.writeheader()
        for u in users:
            writer.writerow({k: str(v) if v is not None else "" for k, v in u.items()})
    buf.seek(0)
    from aiogram.types import BufferedInputFile
    filename = f"users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    await message.answer_document(
        BufferedInputFile(buf.read().encode(), filename=filename),
        caption=f"📤 <b>User Export</b> — {len(users)} records"
    )


# ── /setwelcome ───────────────────────────────────────────────────────────────
@router.message(Command("setwelcome"))
async def cmd_setwelcome(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        current = await db.get_setting(pool, "WELCOME_TEXT", "")
        await message.answer(
            f"📝 <b>Current welcome message:</b>\n\n{current}\n\n"
            f"Usage: /setwelcome <new text>\n"
            f"Variables: {{name}}, {{telegram_id}}, {{user_id}}, {{username}}"
        )
        return
    await db.set_setting(pool, "WELCOME_TEXT", parts[1], message.from_user.id)
    await message.answer("✅ Welcome message updated.")


# ── /setloggroup ──────────────────────────────────────────────────────────────
@router.message(Command("setloggroup"))
async def cmd_setloggroup(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user, level=2):
        return
    chat_id = message.chat.id
    await db.set_log_group(pool, chat_id, message.from_user.id)
    await message.answer(
        f"✅ <b>Log group set</b> to this chat.\n"
        f"Chat ID: <code>{chat_id}</code>\n\n"
        f"All join notifications will be forwarded here."
    )


# ── /cmdtoggle ────────────────────────────────────────────────────────────────
@router.message(Command("cmdtoggle"))
async def cmd_cmdtoggle(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user, level=2):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /cmdtoggle <command_name>")
        return
    name = parts[1].lstrip("/").lower()
    new_state = await db.toggle_command(pool, name)
    if new_state is None:
        await message.answer(f"❌ Command /{name} not found.")
    else:
        state_str = "✅ Enabled" if new_state else "❌ Disabled"
        await message.answer(f"/{name} is now {state_str}.")


# ── /setsetting ───────────────────────────────────────────────────────────────
@router.message(Command("setsetting"))
async def cmd_setsetting(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user, level=2):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /setsetting KEY VALUE")
        return
    key, value = parts[1].upper(), parts[2]
    await db.set_setting(pool, key, value, message.from_user.id)
    await message.answer(f"✅ <code>{key}</code> updated.")


# ── /billing ─────────────────────────────────────────────────────────────────
@router.message(Command("billing"))
async def cmd_billing(message: Message, pool, db_user: dict = None, **_):
    if not await _guard(message, pool, db_user):
        return
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("""
                SELECT COUNT(*) AS total, SUM(AMOUNT) AS revenue
                FROM USER_PAYMENTS WHERE STATUS='PAID'
            """)
            row = await cur.fetchone()
    total = row["total"] or 0
    revenue = float(row["revenue"] or 0)
    await message.answer(
        f"💳 <b>Billing Overview</b>\n\n"
        f"Total payments: <b>{total}</b>\n"
        f"Total revenue: <b>${revenue:,.2f}</b>"
    )