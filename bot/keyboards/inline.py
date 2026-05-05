from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.states import SECTIONS, SECTION_META
from utils.styles import STYLE_PRESETS


# ─────────────────────────────────────────────
# Small UI helpers
# ─────────────────────────────────────────────

TUTORIAL_URL = "https://www.youtube.com/watch?v=VKTDJS7DT08"

def _preset_label(preset: dict) -> str:
    """Human-friendly preset label for Telegram buttons."""
    name = (preset.get("name") or "").strip()
    return name or "Template"


# ═══════════════════════════════════════════
# START / MAIN MENU
# ═══════════════════════════════════════════

def get_start_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Create Website", callback_data="template_menu"),
            InlineKeyboardButton(text="❓ How It Works", callback_data="help_menu"),
        ],
        [
            InlineKeyboardButton(text="📺 Tutorial", url=TUTORIAL_URL),
            InlineKeyboardButton(text="🌐 Website", url="https://imemifybot.online/"),
        ],
        [
            InlineKeyboardButton(text="👥 Community", url="https://t.me/iMemify_bot"),
            InlineKeyboardButton(text="💬 Support", url="https://t.me/ApeNo1"),
        ],
    ])


def get_help_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📺 Tutorial", url=TUTORIAL_URL),
            InlineKeyboardButton(text="💬 Support", url="https://t.me/ApeNo1"),
        ],
        [
            InlineKeyboardButton(text="🌐 Website", url="https://imemifybot.online/"),
            InlineKeyboardButton(text="👥 Community", url="https://t.me/iMemify_bot"),
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="start_menu")],
    ])





def get_template_keyboard(page: int = 1):
    # Sort presets by readable name for a nicer list.
    presets = sorted(STYLE_PRESETS.items(), key=lambda kv: _preset_label(kv[1]).lower())
    mid = (len(presets) + 1) // 2  # split into two pages
    if page == 1:
        page_presets = presets[:mid]
    else:
        page_presets = presets[mid:]

    rows = []
    for i in range(0, len(page_presets), 2):
        row = []
        for j in range(2):
            if i + j < len(page_presets):
                key, preset = page_presets[i + j]
                row.append(InlineKeyboardButton(
                    text=_preset_label(preset),
                    callback_data=f"tpl_{key}"
                ))
        rows.append(row)

    # Navigation row — pagination + back on the same row
    if page == 1:
        rows.append([
            InlineKeyboardButton(text="⬅️ Back", callback_data="start_menu"),
            InlineKeyboardButton(text="More ▶", callback_data="tpl_page_2"),
        ])
    else:
        rows.append([
            InlineKeyboardButton(text="◀ Prev", callback_data="tpl_page_1"),
            InlineKeyboardButton(text="⬅️ Back", callback_data="start_menu"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_global_style_keyboard(page: int = 1):
    """Paginated global style preset picker — mirrors the template keyboard."""
    presets = sorted(STYLE_PRESETS.items(), key=lambda kv: _preset_label(kv[1]).lower())
    mid = (len(presets) + 1) // 2
    if page == 1:
        page_presets = presets[:mid]
    else:
        page_presets = presets[mid:]

    rows = []
    for i in range(0, len(page_presets), 2):
        row = []
        for j in range(2):
            if i + j < len(page_presets):
                key, preset = page_presets[i + j]
                row.append(InlineKeyboardButton(
                    text=_preset_label(preset),
                    callback_data=f"globalstyle_{key}"
                ))
        rows.append(row)

    if page == 1:
        rows.append([
            InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_hub"),
            InlineKeyboardButton(text="More ▶", callback_data="gstyle_page_2"),
        ])
    else:
        rows.append([
            InlineKeyboardButton(text="◀ Prev", callback_data="gstyle_page_1"),
            InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_hub"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ═══════════════════════════════════════════
# BUILDER HUB — Section Grid
# ═══════════════════════════════════════════

def get_builder_hub_keyboard(site_data: dict):
    """2-column grid of sections with content + enable status + action buttons."""
    def status(section: str) -> str:
        sec_data = site_data.get(section, {})
        is_enabled = sec_data.get("enabled", True)
        has_content = bool(sec_data.get("content"))
        if not is_enabled:
            return "🔴"
        return "✅" if has_content else "⬜"

    rows = []
    for i in range(0, len(SECTIONS), 2):
        row = []
        for j in range(2):
            if i + j < len(SECTIONS):
                sec = SECTIONS[i + j]
                meta = SECTION_META[sec]
                row.append(InlineKeyboardButton(
                    text=f"{status(sec)} {meta['emoji']} {meta['label']}",
                    callback_data=f"sec_{sec}"
                ))
        rows.append(row)

    rows.append([
        InlineKeyboardButton(text="🎨 Style All Sections", callback_data="action_style_all"),
        InlineKeyboardButton(text="👁 Preview Website", callback_data="action_preview")
    ])
    rows.append([
        InlineKeyboardButton(text="⚙️ Manage Sections", callback_data="manage_sections"),
        InlineKeyboardButton(text="🚀 Generate Website", callback_data="action_generate")
    ])
    rows.append([
        InlineKeyboardButton(text="⬅️ Back to Main Menu", callback_data="start_menu"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_manage_sections_keyboard(site_data: dict):
    """Full section on/off manager — each row is a section toggle button."""
    rows = []
    for sec in SECTIONS:
        sec_data = site_data.get(sec, {})
        is_enabled = sec_data.get("enabled", True)
        has_content = bool(sec_data.get("content"))
        meta = SECTION_META[sec]

        # Status icons
        on_off = "🟢 ON " if is_enabled else "🔴 OFF"
        filled = " ✏️" if has_content else ""
        label = f"{on_off} {meta['emoji']} {meta['label']}{filled}"

        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"toggle_sec_{sec}"),
        ])

    rows.append([
        InlineKeyboardButton(text="✅ Enable All", callback_data="enable_all_sections"),
        InlineKeyboardButton(text="❌ Disable All", callback_data="disable_all_sections"),
    ])
    rows.append([
        InlineKeyboardButton(text="⬅️ Back to Builder", callback_data="back_to_hub"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ═══════════════════════════════════════════
# SECTION VIEW — Content/Style/Preview
# ═══════════════════════════════════════════

def get_section_view_keyboard(section: str, is_enabled: bool = True):
    """View a section — edit content, edit style, preview, or go back."""
    toggle_text = "🟢 Enabled (Tap to Disable)" if is_enabled else "🔴 Disabled (Tap to Enable)"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=f"toggle_{section}")],
        [InlineKeyboardButton(text="✏️ Edit Content", callback_data=f"edit_content_{section}")],
        [InlineKeyboardButton(text="🎨 Edit Style", callback_data=f"edit_style_{section}")],
        [InlineKeyboardButton(text="👁 Preview Section", callback_data=f"preview_{section}")],
        [InlineKeyboardButton(text="⬅️ Back to Builder", callback_data="back_to_hub")],
    ])


# ═══════════════════════════════════════════
# STYLE SELECTION
# ═══════════════════════════════════════════

def get_style_keyboard(section: str):
    """Choose a style preset or custom."""
    rows = []
    presets = list(STYLE_PRESETS.items())
    for i in range(0, len(presets), 2):
        row = []
        for j in range(2):
            if i + j < len(presets):
                key, preset = presets[i + j]
                row.append(InlineKeyboardButton(
                    text=preset["name"],
                    callback_data=f"style_{section}_{key}"
                ))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="🖌️ Custom Colors", callback_data=f"style_custom_{section}")])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"sec_{section}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_style_apply_scope_keyboard(section: str):
    """After picking a style — apply to this section only or all sections."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Only This Section", callback_data=f"scope_single_{section}")],
        [InlineKeyboardButton(text="🌐 Apply to All Sections", callback_data=f"scope_all_{section}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"sec_{section}")],
    ])


# ═══════════════════════════════════════════
# AFTER INPUT — Done/Edit Again
# ═══════════════════════════════════════════

def get_after_input_keyboard(section: str):
    """Shown after content or style input is saved."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁 Preview Section", callback_data=f"preview_{section}")],
        [InlineKeyboardButton(text="✏️ Edit Section Again", callback_data=f"sec_{section}")],
        [InlineKeyboardButton(text="🏠 Back to Builder", callback_data="back_to_hub")],
    ])


# ═══════════════════════════════════════════
# PREVIEW / PAYMENT
# ═══════════════════════════════════════════

def get_preview_keyboard(project_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Pay & Deploy (15 USDT)", callback_data=f"pay_{project_id}")],
        [InlineKeyboardButton(text="✏️ Edit Sections", callback_data="back_to_hub")],
        [InlineKeyboardButton(text="⬅️ Back to Main Menu", callback_data="start_menu")],
    ])


def get_payment_keyboard(project_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ I Paid", callback_data=f"verify_tx_{project_id}")],
        [InlineKeyboardButton(text="⬅️ Back to Main Menu", callback_data="start_menu")],
    ])


# ═══════════════════════════════════════════
# ADMIN PANEL KEYBOARDS
# ═══════════════════════════════════════════

def get_admin_menu_keyboard():
    """Main admin panel navigation."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
         InlineKeyboardButton(text="🔍 Funnel", callback_data="admin_funnel")],
        [InlineKeyboardButton(text="👥 Users", callback_data="admin_user_list"),
         InlineKeyboardButton(text="📜 History", callback_data="admin_broadcast_history")],
        [InlineKeyboardButton(text="📣 New Broadcast", callback_data="admin_broadcast_start")],
        [InlineKeyboardButton(text="🔄 Refresh Stats", callback_data="admin_stats")],
    ])


def get_admin_broadcast_confirm_keyboard():
    """Confirm or cancel a broadcast before sending."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Send to All Users", callback_data="admin_broadcast_confirm")],
        [InlineKeyboardButton(text="⬅️ Back to Admin Panel", callback_data="admin_panel")],
    ])


def get_admin_broadcast_presets_keyboard():
    """Select a pre-written broadcast message or type a custom one."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Offer / Discount", callback_data="admin_broadcast_preset_offer")],
        [InlineKeyboardButton(text="🚀 Feature Update", callback_data="admin_broadcast_preset_update")],
        [InlineKeyboardButton(text="⚠️ Maintenance Alert", callback_data="admin_broadcast_preset_alert")],
        [InlineKeyboardButton(text="⬅️ Back to Admin Panel", callback_data="admin_panel")],
    ])


def get_admin_back_keyboard():
    """Simple back-to-admin-panel button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back to Admin Panel", callback_data="admin_panel")],
    ])
