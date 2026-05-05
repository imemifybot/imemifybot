"""
Admin panel handler.
Features:
  - /admin — opens admin panel (admin only)
  - 📊 Stats Dashboard  — total users, sites, revenue, conversion rate
  - 🔍 User Activity Log — funnel drop-off report per step
  - 📣 Broadcast Message — send a message to every user
  - 📜 Broadcast History — see last 5 broadcasts
  - Payment approve/reject (existing)
"""

import os
import logging
import json
import io
import zipfile

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    BufferedInputFile, FSInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import (
    get_project, update_project_status,
    get_admin_stats, get_all_user_ids,
    get_funnel_report, save_broadcast,
    get_broadcast_history,
)
from services.netlify import deploy_to_netlify
from services.renderer import render_template
from keyboards.inline import (
    get_admin_menu_keyboard,
    get_admin_broadcast_confirm_keyboard,
    get_admin_broadcast_presets_keyboard,
    get_admin_back_keyboard,
)

router = Router()
logger = logging.getLogger(__name__)

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
except ValueError:
    ADMIN_ID = 0

# ─── Funnel step labels (human-readable) ─────────────────────────────────────
STEP_LABELS = {
    "start":           "🚀 Bot Started",
    "template_chosen": "🎨 Template Chosen",
    "section_edited":  "✏️ Section Edited",
    "generated":       "📦 Site Generated",
    "payment_started": "💳 Payment Started",
    "paid":            "✅ Paid & Deployed",
}


# ─── FSM for broadcast ────────────────────────────────────────────────────────
class BroadcastState(StatesGroup):
    waiting_for_message = State()


# ═══════════════════════════════════════════════════════════
#  GUARD — only admin can use these
# ═══════════════════════════════════════════════════════════

def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ═══════════════════════════════════════════════════════════
#  /admin COMMAND — opens the panel
# ═══════════════════════════════════════════════════════════

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return
    await state.clear()
    await message.answer(
        "🛡️ **Admin Panel**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Choose an action below:",
        parse_mode="Markdown",
        reply_markup=get_admin_menu_keyboard()
    )


@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    try:
        await callback.message.edit_text(
            "🛡️ **Admin Panel**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Choose an action below:",
            parse_mode="Markdown",
            reply_markup=get_admin_menu_keyboard()
        )
    except Exception:
        await callback.message.answer(
            "🛡️ **Admin Panel**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Choose an action below:",
            parse_mode="Markdown",
            reply_markup=get_admin_menu_keyboard()
        )


# ═══════════════════════════════════════════════════════════
#  📊 STATS DASHBOARD
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return
    await callback.answer()

    s = get_admin_stats()

    # Build bar-style progress for conversion
    filled = int(s['conversion'] / 10)  # out of 10 blocks
    bar = "█" * filled + "░" * (10 - filled)

    text = (
        "📊 **Admin Stats**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "👥 *Users*\n"
        f"  ├ Total:      `{s['total_users']}`\n"
        f"  ├ This week:  `{s['new_users_week']}`\n"
        f"  └ Today:      `{s['new_users_today']}`\n\n"

        "🌐 *Sites Created*\n"
        f"  ├ Total:      `{s['total_sites']}`\n"
        f"  ├ This week:  `{s['sites_week']}`\n"
        f"  └ Today:      `{s['sites_today']}`\n\n"

        "💰 *Revenue (15 USDT/site)*\n"
        f"  ├ Paid total: `{s['paid_sites']}` sites\n"
        f"  ├ This week:  `{s['paid_week']}` sites\n"
        f"  ├ Total:      `{s['revenue_total']} USDT`\n"
        f"  └ This week:  `{s['revenue_week']} USDT`\n\n"

        "📈 *Conversion Rate*\n"
        f"  `[{bar}]` **{s['conversion']}%**\n\n"

        "🏆 *Top Template*\n"
        f"  └ `{s['top_template']}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

    try:
        await callback.message.edit_text(
            text, parse_mode="Markdown",
            reply_markup=get_admin_back_keyboard()
        )
    except Exception:
        await callback.message.answer(
            text, parse_mode="Markdown",
            reply_markup=get_admin_back_keyboard()
        )


# ═══════════════════════════════════════════════════════════
#  🔍 USER ACTIVITY / FUNNEL LOG
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin_funnel")
async def cb_admin_funnel(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return
    await callback.answer()

    rows = get_funnel_report()  # (step, total_events, unique_users)

    if not rows:
        text = (
            "🔍 **User Activity Log**\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📭 No activity recorded yet.\n\n"
            "_Activity is logged as users move through the build flow._"
        )
    else:
        lines = []
        # Find max unique_users to build relative bar
        max_u = max(r[2] for r in rows) or 1
        for step, total_events, unique_users in rows:
            label = STEP_LABELS.get(step, f"🔹 {step}")
            pct = round(unique_users / max_u * 100)
            bar_len = int(unique_users / max_u * 8)
            bar = "█" * bar_len + "░" * (8 - bar_len)
            lines.append(
                f"{label}\n"
                f"  `[{bar}]` {unique_users} users ({pct}%)\n"
                f"  _{total_events} total events_"
            )

        text = (
            "🔍 **User Activity & Funnel Log**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            + "\n\n".join(lines)
            + "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "_Bars are relative to the highest step._"
        )

    try:
        await callback.message.edit_text(
            text, parse_mode="Markdown",
            reply_markup=get_admin_back_keyboard()
        )
    except Exception:
        await callback.message.answer(
            text, parse_mode="Markdown",
            reply_markup=get_admin_back_keyboard()
        )


# ═══════════════════════════════════════════════════════════
#  👤 USER LIST
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin_user_list")
async def cb_admin_user_list(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return
    await callback.answer()

    from database.db import get_all_users
    try:
        users = get_all_users()  # returns list of (user_id, username, created_at)
    except Exception:
        users = []

    if not users:
        text = (
            "👥 **User List**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📭 No users registered yet."
        )
    else:
        lines = []
        for i, row in enumerate(users[:30], 1):  # cap at 30 to avoid msg length limit
            uid = row[0]
            uname = f"@{row[1]}" if row[1] else "_(no username)_"
            date = row[2][:10] if row[2] else "?"
            lines.append(
                f"`{i:02d}.` {uname}\n"
                f"└ ID: `{uid}` • Joined: `{date}`"
            )

        total = len(users)
        shown = min(total, 30)
        text = (
            "👥 **User List**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Total registered users: {total}*\n"
            f"_(showing latest {shown})_\n\n"
            + "\n".join(lines)
        )

    try:
        await callback.message.edit_text(
            text, parse_mode="Markdown",
            reply_markup=get_admin_back_keyboard()
        )
    except Exception:
        await callback.message.answer(
            text, parse_mode="Markdown",
            reply_markup=get_admin_back_keyboard()
        )


# ═══════════════════════════════════════════════════════════
#  📣 BROADCAST MESSAGE
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin_broadcast_start")
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(BroadcastState.waiting_for_message)

    text = (
        "📣 **Broadcast Message**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Choose a pre-written template below or just **type your custom message** to send to all users.\n\n"
        "Supports Markdown formatting:\n"
        "`*bold*`  `_italic_`  `` `code` ``\n\n"
        "_Send /cancel to abort._"
    )
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_admin_broadcast_presets_keyboard())
    except Exception:
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=get_admin_broadcast_presets_keyboard())


@router.callback_query(F.data.startswith("admin_broadcast_preset_"))
async def cb_broadcast_preset(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return
        
    preset_type = callback.data.replace("admin_broadcast_preset_", "")
    
    presets = {
        "offer": "🎉 **Special Offer!**\n\nFor a limited time, build your meme coin website with premium templates at a discounted rate. Don't miss out on launching your project to the moon! 🚀\n\n👉 Type /start to begin building now.",
        "update": "🚀 **New Feature Update!**\n\nWe've just added brand new templates and features to the Meme Website Builder. Check out the latest designs to make your coin stand out from the crowd!\n\n👉 Type /start to explore.",
        "alert": "⚠️ **System Update**\n\nWe are currently performing scheduled maintenance to improve bot performance. You may experience slight delays, but your data is safe.\n\nThank you for your patience!"
    }
    
    broadcast_text = presets.get(preset_type, "")
    if not broadcast_text:
        await callback.answer("Unknown preset.", show_alert=True)
        return
        
    await state.update_data(broadcast_text=broadcast_text)
    await state.set_state(None)
    
    preview = broadcast_text[:80] + ("..." if len(broadcast_text) > 80 else "")
    confirm_text = (
        "📣 **Confirm Broadcast**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"**Preview:**\n{preview}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        "This will be sent to **all registered users**. Confirm?"
    )
    
    try:
        await callback.message.edit_text(
            confirm_text,
            parse_mode="Markdown",
            reply_markup=get_admin_broadcast_confirm_keyboard()
        )
    except Exception:
        await callback.message.answer(
            confirm_text,
            parse_mode="Markdown",
            reply_markup=get_admin_broadcast_confirm_keyboard()
        )


@router.message(BroadcastState.waiting_for_message)
async def handle_broadcast_input(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return

    if message.text and message.text.strip().lower() in ("/cancel", "cancel"):
        await state.clear()
        await message.answer(
            "❌ Broadcast cancelled.",
            reply_markup=get_admin_back_keyboard()
        )
        return

    broadcast_text = message.text or message.caption or ""
    if not broadcast_text.strip():
        await message.answer("⚠️ Please send a text message to broadcast.")
        return

    # Store the pending broadcast text and ask for confirmation
    await state.update_data(broadcast_text=broadcast_text)
    await state.set_state(None)

    preview = broadcast_text[:80] + ("..." if len(broadcast_text) > 80 else "")
    confirm_text = (
        "📣 **Confirm Broadcast**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"**Preview:**\n{preview}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        "This will be sent to **all registered users**. Confirm?"
    )
    await message.answer(
        confirm_text,
        parse_mode="Markdown",
        reply_markup=get_admin_broadcast_confirm_keyboard()
    )


@router.callback_query(F.data == "admin_broadcast_confirm")
async def cb_broadcast_confirm(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")
    if not broadcast_text:
        await callback.answer("⚠️ No message to send.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        "📣 **Sending broadcast...**\n\n⏳ Please wait...",
        parse_mode="Markdown"
    )

    user_ids = get_all_user_ids()
    sent = 0
    failed = 0

    for uid in user_ids:
        try:
            await callback.bot.send_message(
                chat_id=uid,
                text=f"📢 **Announcement**\n\n{broadcast_text}",
                parse_mode="Markdown"
            )
            sent += 1
        except Exception as e:
            logger.warning(f"Broadcast failed for user {uid}: {e}")
            failed += 1

    # Persist the broadcast
    save_broadcast(callback.from_user.id, broadcast_text, sent, failed)
    await state.clear()

    result_text = (
        "📣 **Broadcast Complete!**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Sent:   `{sent}` users\n"
        f"❌ Failed: `{failed}` users\n"
        f"📊 Total:  `{len(user_ids)}` users"
    )
    try:
        await callback.message.edit_text(
            result_text, parse_mode="Markdown",
            reply_markup=get_admin_back_keyboard()
        )
    except Exception:
        await callback.message.answer(
            result_text, parse_mode="Markdown",
            reply_markup=get_admin_back_keyboard()
        )


# ═══════════════════════════════════════════════════════════
#  📜 BROADCAST HISTORY
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin_broadcast_history")
async def cb_broadcast_history(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return
    await callback.answer()

    history = get_broadcast_history(limit=5)  # (id, message, sent, failed, created_at)

    if not history:
        text = (
            "📜 **Broadcast History**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📭 No broadcasts sent yet."
        )
    else:
        lines = []
        for bid, msg_text, total_sent, total_failed, created_at in history:
            preview = msg_text[:80] + ("..." if len(msg_text) > 80 else "")
            # Format date nicely
            date_str = created_at[:16] if created_at else "Unknown"
            lines.append(
                f"🔹 **#{bid}** — `{date_str}`\n"
                f"  ✅ {total_sent} sent  ❌ {total_failed} failed\n"
                f"  _{preview}_"
            )
        text = (
            "📜 **Last 5 Broadcasts**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            + "\n\n".join(lines)
        )

    try:
        await callback.message.edit_text(
            text, parse_mode="Markdown",
            reply_markup=get_admin_back_keyboard()
        )
    except Exception:
        await callback.message.answer(
            text, parse_mode="Markdown",
            reply_markup=get_admin_back_keyboard()
        )


# ═══════════════════════════════════════════════════════════
#  PAYMENT APPROVE / REJECT  (existing functionality)
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin_approve_"))
async def admin_approve_payment(callback: CallbackQuery):
    _, _, project_id_str, user_id_str = callback.data.split("_", 3)
    project_id = int(project_id_str)
    user_id = int(user_id_str)

    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ **Status: Approved. Deploying...**",
        parse_mode="Markdown"
    )

    project = get_project(project_id)
    if not project:
        await callback.message.answer("❌ Project not found in database.")
        return

    project_data = json.loads(project['data'])

    try:
        html_content = render_template(project['template'], project_data)
    except Exception as e:
        logger.error(f"Template render failed for project {project_id}: {e}")
        await callback.message.answer(f"❌ Template render failed: {str(e)}")
        return

    try:
        site_url = await deploy_to_netlify(html_content, f"crypto-site-{project_id}")
        update_project_status(project_id, paid=True, site_url=site_url)

        # Log payment activity
        try:
            from database.db import log_activity
            log_activity(user_id, "paid", site_url)
        except Exception:
            pass

        # Create ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            zip_file.writestr("index.html", html_content)
        zip_buffer.seek(0)

        document = BufferedInputFile(
            zip_buffer.read(),
            filename=f"website_files_{project_id}.zip"
        )

        try:
            caption_text = (
                f"🎉 **Your Website is Live & Ready!**\n\n"
                f"Your meme coin project has been successfully deployed and the source code is attached below.\n\n"
                f"**What's next?**\n"
                f"• Preview your live site\n"
                f"• Download the ZIP for backup\n"
                f"• Host it on your own custom domain!"
            )

            success_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌐 View Live Website", url=site_url)],
                [InlineKeyboardButton(text="🔗 Host on Custom Domain (Tutorial)",
                                      url="https://www.youtube.com/watch?v=eY8dmF0a95g")]
            ])

            photo_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "thanks.png"
            )

            if os.path.exists(photo_path):
                photo = FSInputFile(photo_path)
                await callback.bot.send_photo(
                    chat_id=user_id, photo=photo,
                    caption=caption_text, parse_mode="Markdown",
                    reply_markup=success_keyboard
                )
                await callback.bot.send_document(
                    chat_id=user_id, document=document,
                    caption="📦 **Source Code (.zip)**", parse_mode="Markdown"
                )
            else:
                await callback.bot.send_document(
                    chat_id=user_id, document=document,
                    caption=caption_text, parse_mode="Markdown",
                    reply_markup=success_keyboard
                )

            await callback.message.edit_text(
                f"{callback.message.text}\n✅ **Deployed Successfully! User notified and ZIP sent.**\n🌐 Site: [Link]({site_url})",
                parse_mode="Markdown"
            )
        except Exception as e:
            await callback.message.answer(
                f"Deployed to {site_url}, but failed to notify user {user_id}. Error: {e}"
            )

    except Exception as e:
        logger.error(f"Deployment failed for project {project_id}: {e}")
        await callback.message.answer(f"❌ Deployment failed: {str(e)}")


@router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_payment(callback: CallbackQuery):
    _, _, project_id_str, user_id_str = callback.data.split("_", 3)
    project_id = int(project_id_str)
    user_id = int(user_id_str)

    await callback.message.edit_text(
        f"{callback.message.text}\n\n❌ **Status: Rejected.**",
        parse_mode="Markdown"
    )

    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=f"❌ **Payment Rejected**\n\n"
                 f"Your payment verification for Project ID `{project_id}` was rejected by the admin. "
                 "Please ensure you sent the correct amount and provided the correct transaction hash.\n\n"
                 "If you think this is a mistake, please contact support.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await callback.message.answer(f"Failed to notify user {user_id}. Error: {e}")
