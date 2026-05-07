"""
Section-based website builder handler.
No more 44-step flow — each section is 1 message for content, 1 click for style.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from utils.states import BuilderState, SECTIONS, SECTION_META
from utils.styles import STYLE_PRESETS, DEFAULT_STYLE, parse_style_input, merge_style
from utils.parser import parse_content_input, format_section_summary
from services.renderer import render_template, save_preview
from database.db import create_project, log_activity
from keyboards.inline import (
    get_builder_hub_keyboard,
    get_manage_sections_keyboard,
    get_section_view_keyboard,
    get_style_keyboard,
    get_style_apply_scope_keyboard,
    get_after_input_keyboard,
    get_preview_keyboard,
    get_global_style_keyboard,
)
import logging
import base64
from io import BytesIO
import re

router = Router()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════

def get_site_data(data: dict) -> dict:
    """Get the site_data dict from FSM state, initializing if needed."""
    return data.get("site_data", {})


def build_template_data(site_data: dict) -> dict:
    """Convert site_data into the format expected by the Jinja2 template."""
    result = {}
    for section in SECTIONS:
        sec = site_data.get(section, {})
        content = sec.get("content", {})
        style = sec.get("style", {})
        is_enabled = sec.get("enabled", True)
        
        # Merge with defaults if content not set
        if not content:
            defaults = SECTION_META.get(section, {}).get("defaults", {})
            content = defaults.copy()
        
        # Merge style with defaults
        if not style:
            style = DEFAULT_STYLE.copy()
        
        result[section] = {"content": content, "style": style, "enabled": is_enabled}

    nav_sections = [
        ("hero", "Home", "home"),
        ("about", "About", "about"),
        ("tokenomics", "Tokenomics", "tokenomics"),
        ("buy", "How To Buy", "buy"),
        ("roadmap", "Roadmap", "roadmap"),
        ("socials", "Socials", "socials"),
        ("footer", "Footer", "footer"),
    ]
    nav_items = [
        {"section": section, "label": label, "anchor": anchor}
        for section, label, anchor in nav_sections
        if result[section]["enabled"]
    ]

    hero_secondary = next(
        (
            item
            for item in nav_items
            if item["section"] in {"buy", "about", "tokenomics", "roadmap", "socials", "footer"}
        ),
        None,
    )
    about_cta = next(
        (
            item
            for item in nav_items
            if item["section"] in {"tokenomics", "buy", "roadmap", "socials", "footer"}
        ),
        None,
    )

    result["site"] = {
        "nav_items": nav_items,
        "home_anchor": f"#{nav_items[0]['anchor']}" if nav_items else "#",
        "hero_secondary": hero_secondary,
        "about_cta": about_cta,
        # Global coin image — set once in header, available everywhere
        "coin_image": site_data.get("header", {}).get("content", {}).get("logo_image", ""),
    }
    
    return result


async def safe_reply(target, text: str, reply_markup=None):
    """Send or edit a message, handling photo/text transitions and plain messages."""
    # Plain Message (not from a callback) — just answer
    if isinstance(target, Message):
        await target.answer(text, reply_markup=reply_markup, parse_mode="Markdown")
        return
    # CallbackQuery.message — try edit first, fall back to answer
    try:
        await target.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        logger.debug(f"safe_reply edit_text failed: {e}")
        try:
            await target.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as e2:
            logger.debug(f"safe_reply edit_caption failed: {e2}")
            if hasattr(target, 'answer'):
                await target.answer(text, reply_markup=reply_markup, parse_mode="Markdown")


async def show_hub(target, state: FSMContext):
    """Show the builder hub with section grid."""
    data = await state.get_data()
    site_data = get_site_data(data)
    await state.set_state(None)

    text = (
        "🛠️ **Website Builder**\n\n"
        "Choose a section to edit, or tap **🎨 Style All Sections** to apply one style to all sections.\n\n"
        "_⬜ = Enabled (no content yet) | ✅ = Filled | 🔴 = Disabled_"
    )
    await safe_reply(target, text, reply_markup=get_builder_hub_keyboard(site_data))


async def show_manage_sections(target, state: FSMContext):
    """Show the manage-sections toggle screen."""
    data = await state.get_data()
    site_data = get_site_data(data)

    text = (
        "⚙️ **Manage Sections**\n\n"
        "Tap a section to toggle it *ON* or *OFF*.\n"
        "_Disabled sections are hidden on the website._\n\n"
        "🟢 ON  |  🔴 OFF  |  ✏️ Has content"
    )
    await safe_reply(target, text, reply_markup=get_manage_sections_keyboard(site_data))


async def show_section_view(target, state: FSMContext, section: str):
    """Show section detail view with content summary."""
    data = await state.get_data()
    site_data = get_site_data(data)
    sec_data = site_data.get(section, {})
    content = sec_data.get("content", {})
    style = sec_data.get("style", {})
    is_enabled = sec_data.get("enabled", True)
    
    meta = SECTION_META[section]
    summary = format_section_summary(section, content, style)
    
    text = (
        f"{meta['emoji']} **{meta['label']}**\n\n"
        f"**Status:** {'🟢 Enabled' if is_enabled else '🔴 Disabled'}\n\n"
        f"{summary}\n\n"
        "Choose an action:"
    )
    await safe_reply(target, text, reply_markup=get_section_view_keyboard(section, is_enabled))


async def _extract_image_data_url(message: Message) -> str | None:
    """Return a base64 data URL from a photo/document message if present."""
    file_id = None
    mime_type = "image/jpeg"

    if message.photo:
        file_id = message.photo[-1].file_id
        mime_type = "image/jpeg"
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        file_id = message.document.file_id
        mime_type = message.document.mime_type

    if not file_id:
        return None

    file_info = await message.bot.get_file(file_id)
    buffer = BytesIO()
    await message.bot.download_file(file_info.file_path, destination=buffer)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _resolve_image_field(section: str, source_text: str, existing_content: dict, content: dict) -> str | None:
    """Resolve which content image field should receive the uploaded image."""
    lower_text = (source_text or "").lower()

    if section == "header":
        return "logo_image"
    if section == "hero":
        return "hero_image"
    if section == "about":
        return "about_image"
    if section == "tokenomics":
        return "tokenomics_image"

    if section == "buy":
        explicit = re.search(r"field\s*:\s*([a-z0-9_]+)", lower_text)
        if explicit:
            field = explicit.group(1).strip()
            if field in {"buy_step_1_image", "buy_step_2_image", "buy_step_3_image"}:
                return field

        if "step 1" in lower_text:
            return "buy_step_1_image"
        if "step 2" in lower_text:
            return "buy_step_2_image"
        if "step 3" in lower_text:
            return "buy_step_3_image"

        for field in ("buy_step_1_image", "buy_step_2_image", "buy_step_3_image"):
            if not content.get(field) and not existing_content.get(field):
                return field
        return "buy_step_1_image"

    return None


# ═══════════════════════════════════════════════════════
#  NAVIGATION CALLBACKS
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "back_to_hub")
async def back_to_hub(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(None)
    await show_hub(callback.message, state)


@router.callback_query(F.data.startswith("sec_"))
async def section_selected(callback: CallbackQuery, state: FSMContext):
    """User tapped a section in the hub grid."""
    section = callback.data.replace("sec_", "")
    if section not in SECTIONS:
        await callback.answer("Unknown section", show_alert=True)
        return
    await callback.answer()
    await state.update_data(current_section=section)
    await show_section_view(callback.message, state, section)


@router.callback_query(F.data.startswith("toggle_sec_"))
async def toggle_section_from_manager(callback: CallbackQuery, state: FSMContext):
    """Toggle a section on/off directly from the Manage Sections screen."""
    section = callback.data.replace("toggle_sec_", "")
    if section not in SECTIONS:
        await callback.answer("Unknown section", show_alert=True)
        return

    data = await state.get_data()
    site_data = get_site_data(data)

    if section not in site_data:
        site_data[section] = {}

    is_enabled = site_data[section].get("enabled", True)
    site_data[section]["enabled"] = not is_enabled
    new_state = "Enabled" if not is_enabled else "Disabled"

    await state.update_data(site_data=site_data)
    await callback.answer(f"{SECTION_META[section]['emoji']} {SECTION_META[section]['label']} {new_state}!")
    await show_manage_sections(callback.message, state)


@router.callback_query(F.data.startswith("toggle_") & ~F.data.startswith("toggle_sec_"))
async def toggle_section(callback: CallbackQuery, state: FSMContext):
    """Toggle a section's enabled/disabled state (from section detail view)."""
    section = callback.data.replace("toggle_", "")
    if section not in SECTIONS:
        await callback.answer("Unknown section", show_alert=True)
        return

    data = await state.get_data()
    site_data = get_site_data(data)

    if section not in site_data:
        site_data[section] = {}

    is_enabled = site_data[section].get("enabled", True)
    site_data[section]["enabled"] = not is_enabled

    await state.update_data(site_data=site_data)
    await callback.answer(f"Section {'disabled' if is_enabled else 'enabled'}")
    await show_section_view(callback.message, state, section)


@router.callback_query(F.data == "manage_sections")
async def open_manage_sections(callback: CallbackQuery, state: FSMContext):
    """Open the Manage Sections panel."""
    await callback.answer()
    await show_manage_sections(callback.message, state)


@router.callback_query(F.data == "enable_all_sections")
async def enable_all_sections(callback: CallbackQuery, state: FSMContext):
    """Enable all sections at once."""
    data = await state.get_data()
    site_data = get_site_data(data)

    for sec in SECTIONS:
        if sec not in site_data:
            site_data[sec] = {}
        site_data[sec]["enabled"] = True

    await state.update_data(site_data=site_data)
    await callback.answer("✅ All sections enabled!")
    await show_manage_sections(callback.message, state)


@router.callback_query(F.data == "disable_all_sections")
async def disable_all_sections(callback: CallbackQuery, state: FSMContext):
    """Disable all sections at once."""
    data = await state.get_data()
    site_data = get_site_data(data)

    for sec in SECTIONS:
        if sec not in site_data:
            site_data[sec] = {}
        site_data[sec]["enabled"] = False

    await state.update_data(site_data=site_data)
    await callback.answer("🔴 All sections disabled!")
    await show_manage_sections(callback.message, state)


# ═══════════════════════════════════════════════════════
#  CONTENT EDITING
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("edit_content_"))
async def start_content_edit(callback: CallbackQuery, state: FSMContext):
    """Show the content prompt for a section — user sends ONE message."""
    section = callback.data.replace("edit_content_", "")
    if section not in SECTIONS:
        await callback.answer("Unknown section", show_alert=True)
        return
    
    meta = SECTION_META[section]
    await state.set_state(BuilderState.editing_content)
    await state.update_data(current_section=section)
    
    await safe_reply(callback.message, meta["content_prompt"])
    await callback.answer()


@router.message(BuilderState.editing_content)
async def handle_content_input(message: Message, state: FSMContext):
    """Process the ONE-message content input."""
    data = await state.get_data()
    section = data.get("current_section")
    
    if not section or section not in SECTIONS:
        await message.answer("⚠️ Something went wrong. Please go back to the hub.")
        await state.set_state(None)
        return
    
    meta = SECTION_META[section]
    site_data = get_site_data(data)
    existing_content = site_data.get(section, {}).get("content", {})
    
    # Handle skip
    if message.text and message.text.strip().lower() == "skip":
        content = meta["defaults"].copy()
    else:
        # Parse the message
        source_text = message.text or message.caption or ""
        content = parse_content_input(source_text, section, meta["content_fields"])

        # Image upload support (photo/document) for sections with image fields
        uploaded_image = await _extract_image_data_url(message)
        if uploaded_image:
            image_field = _resolve_image_field(section, source_text, existing_content, content)
            if image_field:
                content[image_field] = uploaded_image
        
        # Fill missing fields with existing values, then defaults
        for field in meta["content_fields"]:
            if field not in content:
                if existing_content.get(field):
                    content[field] = existing_content[field]
                else:
                    content[field] = meta["defaults"].get(field, "")
    
    # Save to site_data
    if section not in site_data:
        site_data[section] = {}
    site_data[section]["content"] = content

    # ── Logo propagation ────────────────────────────────────────────
    # When the user uploads a logo image in the Header section,
    # automatically copy it to other sections as the default coin image
    # (only if those sections don't already have their own custom image).
    if section == "header" and content.get("logo_image"):
        coin_img = content["logo_image"]
        propagate = {
            "hero":       "hero_image",
            "about":      "about_image",
            "tokenomics": "tokenomics_image",
        }
        for sec_name, img_field in propagate.items():
            if sec_name not in site_data:
                site_data[sec_name] = {}
            if "content" not in site_data[sec_name]:
                site_data[sec_name]["content"] = {}
            # Only overwrite if no custom image is already set
            if not site_data[sec_name]["content"].get(img_field):
                site_data[sec_name]["content"][img_field] = coin_img
    # ────────────────────────────────────────────────────────────────

    await state.update_data(site_data=site_data)
    await state.set_state(None)
    
    # Log activity
    log_activity(message.from_user.id, "section_edited", section)
    
    # Show confirmation
    summary = format_section_summary(section, content, site_data[section].get("style", {}))
    await message.answer(
        f"✅ **{meta['emoji']} {meta['label']} — Saved!**\n\n{summary}",
        parse_mode="Markdown",
        reply_markup=get_after_input_keyboard(section)
    )


# ═══════════════════════════════════════════════════════
#  STYLE EDITING
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("edit_style_"))
async def start_style_edit(callback: CallbackQuery, state: FSMContext):
    """Show style preset menu for a section."""
    section = callback.data.replace("edit_style_", "")
    if section not in SECTIONS:
        await callback.answer("Unknown section", show_alert=True)
        return
    
    await callback.answer()
    await state.update_data(current_section=section)
    
    text = (
        f"🎨 **Style — {SECTION_META[section]['label']}**\n\n"
        "Choose a preset or enter custom colors."
    )
    await safe_reply(callback.message, text, reply_markup=get_style_keyboard(section))


@router.callback_query(F.data.startswith("style_") & ~F.data.startswith("style_custom_"))
async def apply_style_preset(callback: CallbackQuery, state: FSMContext):
    """Apply a style preset to a section."""
    # Format: style_{section}_{preset_key}
    # We split on "_" with maxsplit=2 after stripping the "style_" prefix
    raw = (callback.data or "")[len("style_"):]
    # Find which section name matches (sections can't have underscores, presets can)
    section = None
    preset_key = None
    for sec in SECTIONS:
        if raw.startswith(sec + "_"):
            section = sec
            preset_key = raw[len(sec) + 1:]
            break

    if not section or not preset_key or preset_key not in STYLE_PRESETS:
        await callback.answer("Unknown preset", show_alert=True)
        return

    await callback.answer()

    # Store the pending style for scope selection
    preset = STYLE_PRESETS[preset_key].copy()
    preset.pop("name", None)
    await state.update_data(current_section=section, pending_style=preset)

    preset_name = STYLE_PRESETS[preset_key]["name"]
    text = (
        f"🎨 Selected: **{preset_name}**\n\n"
        "Apply to which sections?"
    )
    await safe_reply(callback.message, text, reply_markup=get_style_apply_scope_keyboard(section))


@router.callback_query(F.data.startswith("scope_single_"))
async def scope_single(callback: CallbackQuery, state: FSMContext):
    """Apply pending style to the current section only."""
    section = callback.data.replace("scope_single_", "")
    data = await state.get_data()
    pending_style = data.get("pending_style", DEFAULT_STYLE.copy())
    site_data = get_site_data(data)
    
    if section not in site_data:
        site_data[section] = {}
    site_data[section]["style"] = pending_style
    
    await state.update_data(site_data=site_data, pending_style=None)
    await callback.answer("✅ Style applied!")
    await show_section_view(callback.message, state, section)


@router.callback_query(F.data.startswith("scope_all_"))
async def scope_all(callback: CallbackQuery, state: FSMContext):
    """Apply pending style to ALL sections."""
    data = await state.get_data()
    pending_style = data.get("pending_style", DEFAULT_STYLE.copy())
    site_data = get_site_data(data)
    
    for sec in SECTIONS:
        if sec not in site_data:
            site_data[sec] = {}
        site_data[sec]["style"] = pending_style.copy()
    
    await state.update_data(site_data=site_data, pending_style=None)
    await callback.answer("✅ Style applied to all sections!")
    await show_hub(callback.message, state)


@router.callback_query(F.data.startswith("style_custom_"))
async def start_custom_style(callback: CallbackQuery, state: FSMContext):
    """Start custom style input mode."""
    section = callback.data.replace("style_custom_", "")
    if section not in SECTIONS:
        await callback.answer("Unknown section", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(BuilderState.editing_style)
    await state.update_data(current_section=section)
    
    text = (
        "🖌️ **Custom Style**\n\n"
        "Send ONE message with:\n"
        "```\n"
        "Background: #000000\n"
        "Text: #ffffff\n"
        "Button: #FF3B3B\n"
        "Button Text: #ffffff\n"
        "Style: rounded\n"
        "```\n\n"
        "_Style options: rounded, pill, square_"
    )
    await safe_reply(callback.message, text)


@router.message(BuilderState.editing_style)
async def handle_style_input(message: Message, state: FSMContext):
    """Process custom style input."""
    data = await state.get_data()
    section = data.get("current_section")
    
    if not section or section not in SECTIONS:
        await message.answer("⚠️ Error. Please go back to the hub.")
        await state.set_state(None)
        return
    

    
    if message.text and message.text.strip().lower() == "skip":
        style = DEFAULT_STYLE.copy()
    else:
        parsed = parse_style_input(message.text or "")
        style = merge_style(DEFAULT_STYLE, parsed)
    
    # Store pending for scope selection
    await state.update_data(pending_style=style, current_section=section)
    await state.set_state(None)
    
    text = "🎨 **Custom style parsed!**\n\nApply to which sections?"
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_style_apply_scope_keyboard(section)
    )


# ═══════════════════════════════════════════════════════
#  STYLE ALL (FROM HUB)
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "action_style_all")
async def style_all_from_hub(callback: CallbackQuery, state: FSMContext):
    """Show global style preset picker (applies to all sections)."""
    await callback.answer()
    await state.update_data(current_section="header")
    text = "🎨 **Global Style**\n\nChoose a style to apply to all sections."
    await safe_reply(callback.message, text, reply_markup=get_global_style_keyboard(page=1))


@router.callback_query(F.data == "gstyle_page_1")
async def gstyle_page_1(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=get_global_style_keyboard(page=1))
    except Exception:
        pass


@router.callback_query(F.data == "gstyle_page_2")
async def gstyle_page_2(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=get_global_style_keyboard(page=2))
    except Exception:
        pass


@router.callback_query(F.data.startswith("globalstyle_"))
async def apply_global_style(callback: CallbackQuery, state: FSMContext):
    """Apply a style preset to ALL sections at once."""
    preset_key = callback.data.replace("globalstyle_", "")
    if preset_key not in STYLE_PRESETS:
        await callback.answer("Unknown preset", show_alert=True)
        return
    
    preset = STYLE_PRESETS[preset_key].copy()
    preset.pop("name", None)
    
    data = await state.get_data()
    site_data = get_site_data(data)
    
    for sec in SECTIONS:
        if sec not in site_data:
            site_data[sec] = {}
        site_data[sec]["style"] = preset.copy()
    
    await state.update_data(site_data=site_data)
    await callback.answer(f"✅ {STYLE_PRESETS[preset_key]['name']} applied to all!")
    await show_hub(callback.message, state)


# ═══════════════════════════════════════════════════════
#  PREVIEW
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("preview_"))
async def preview_section(callback: CallbackQuery, state: FSMContext):
    """Generate and send a preview of the current website."""
    section = callback.data.replace("preview_", "")
    await callback.answer()
    
    data = await state.get_data()
    site_data = get_site_data(data)
    template_data = build_template_data(site_data)
    
    try:
        html = render_template("memecoin", template_data, is_preview=True)
        preview_path = save_preview(html, f"preview_{section}")
        
        file = FSInputFile(preview_path)
        await callback.message.answer_document(
            document=file,
            caption=f"👁 **Preview** — after editing {SECTION_META.get(section, {}).get('label', section)}\n\nOpen in browser to see your website.",
            parse_mode="Markdown",
            reply_markup=get_after_input_keyboard(section)
        )
    except Exception as e:
        logger.error(f"Preview failed: {e}")
        await callback.message.answer(f"❌ Preview failed: {str(e)}")


@router.callback_query(F.data == "action_preview")
async def preview_full(callback: CallbackQuery, state: FSMContext):
    """Full website preview from the hub."""
    await callback.answer()
    
    data = await state.get_data()
    site_data = get_site_data(data)
    template_data = build_template_data(site_data)
    
    try:
        html = render_template("memecoin", template_data, is_preview=True)
        preview_path = save_preview(html, "full_preview")
        
        file = FSInputFile(preview_path)
        await callback.message.answer_document(
            document=file,
            caption="👁 **Full Website Preview**\n\nDownload and open in your browser.",
            parse_mode="Markdown",
            reply_markup=get_after_input_keyboard("header")
        )
    except Exception as e:
        logger.error(f"Preview failed: {e}")
        await callback.message.answer(f"❌ Preview failed: {str(e)}")


# ═══════════════════════════════════════════════════════
#  GENERATE / PUBLISH
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "action_generate")
async def generate_website(callback: CallbackQuery, state: FSMContext):
    """Generate final website and show payment options."""
    await callback.answer()
    
    data = await state.get_data()
    site_data = get_site_data(data)
    
    if not site_data:
        await callback.message.answer("⚠️ Please edit at least one section first!")
        return
    
    user_id = callback.from_user.id if callback.from_user else 0
    template_data = build_template_data(site_data)
    
    await callback.message.answer("⏳ Generating your website...")
    
    try:
        project_id = create_project(user_id, "memecoin", template_data)
        html = render_template("memecoin", template_data, is_preview=True)
        preview_path = save_preview(html, project_id)
        
        # Log activity
        log_activity(user_id, "generated", f"project_{project_id}")
        
        file = FSInputFile(preview_path)
        await callback.message.answer_document(
            document=file,
            caption=(
                "🎉 **Website Generated!**\n\n"
                "📂 Download and preview in your browser.\n\n"
                "Ready to deploy? Complete payment to get your live URL."
            ),
            parse_mode="Markdown",
            reply_markup=get_preview_keyboard(project_id)
        )
    except Exception as e:
        logger.error(f"Generate failed: {e}")
        await callback.message.answer(f"❌ Generation failed: {str(e)}")
