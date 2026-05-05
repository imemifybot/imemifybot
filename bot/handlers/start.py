import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from keyboards.inline import get_start_keyboard, get_template_keyboard, get_help_keyboard
from database.db import add_user, log_activity

router = Router()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WELCOME_IMAGE = os.path.join(BASE_DIR, "assets", "banner_welcome.png")
TEMPLATE_IMAGE = os.path.join(BASE_DIR, "assets", "banner_template.png")
HELP_IMAGE = os.path.join(BASE_DIR, "assets", "banner_help.png")

WELCOME_TEXT = (
    "🚀 *Meme Website Builder*\n\n"
    "1) Pick a template\n"
    "2) Edit your content\n"
    "3) Preview and deploy\n\n"
    "Choose an option below:"
)

HELP_TEXT = (
    "❓ *How It Works (Step-by-Step)*\n\n"
    "1️⃣ **Choose a Template**\n"
    "Tap *Create Website* and pick the style you like.\n\n"
    "2️⃣ **Edit Sections**\n"
    "Open each section (Hero, About, Tokenomics, Buy, Roadmap, Socials).\n"
    "Add your coin name, text, links, and contract.\n\n"
    "3️⃣ **Style It**\n"
    "Apply presets or custom colors to match your brand.\n\n"
    "4️⃣ **Preview**\n"
    "Use preview before publish to check desktop/mobile layout.\n\n"
    "5️⃣ **Generate & Pay**\n"
    "Generate website, complete payment, and submit Tx hash.\n\n"
    "6️⃣ **Admin Approval & Deploy**\n"
    "After approval, your live URL and ZIP are sent automatically.\n\n"
    "💡 *Tip:* Send `skip` while editing to use defaults quickly."
)

HELP_EXAMPLE_TEXT = (
    "🖼️ *Template Example*\n\n"
    "This is a sample template preview screen.\n"
    "After choosing a template, you'll edit content section-by-section."
)


async def _send_help_example(target_message: Message):
    """Send a secondary visual example for the help flow."""
    template_photo = FSInputFile(TEMPLATE_IMAGE)
    try:
        await target_message.answer_photo(
            photo=template_photo,
            caption=HELP_EXAMPLE_TEXT,
            parse_mode="Markdown",
            reply_markup=get_help_keyboard(),
        )
    except Exception:
        await target_message.answer(
            HELP_EXAMPLE_TEXT,
            parse_mode="Markdown",
            reply_markup=get_help_keyboard(),
        )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    add_user(
        message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    log_activity(message.from_user.id, "start")
    photo = FSInputFile(WELCOME_IMAGE)
    try:
        await message.answer_photo(
            photo=photo,
            caption=WELCOME_TEXT,
            parse_mode="Markdown",
            reply_markup=get_start_keyboard()
        )
    except Exception:
        await message.answer(
            WELCOME_TEXT,
            parse_mode="Markdown",
            reply_markup=get_start_keyboard()
        )


@router.callback_query(F.data == "start_menu")
async def start_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    log_activity(callback.from_user.id, "start")
    photo = FSInputFile(WELCOME_IMAGE)
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=photo,
                caption=WELCOME_TEXT,
                parse_mode="Markdown"
            ),
            reply_markup=get_start_keyboard()
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        try:
            await callback.message.answer_photo(
                photo=photo,
                caption=WELCOME_TEXT,
                parse_mode="Markdown",
                reply_markup=get_start_keyboard()
            )
        except Exception:
            await callback.message.answer(
                WELCOME_TEXT,
                parse_mode="Markdown",
                reply_markup=get_start_keyboard()
            )




@router.callback_query(F.data == "template_menu")
async def template_menu(callback: CallbackQuery):
    await callback.answer()
    text = (
        "📄 *Choose a Template*\n\n"
        "Pick a style to start your website.\n"
        "_Tip: tap More ▶ for more templates._"
    )
    photo = FSInputFile(TEMPLATE_IMAGE)
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=photo,
                caption=text,
                parse_mode="Markdown"
            ),
            reply_markup=get_template_keyboard(page=1)
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        try:
            await callback.message.answer_photo(
                photo=photo,
                caption=text,
                parse_mode="Markdown",
                reply_markup=get_template_keyboard(page=1)
            )
        except Exception:
            await callback.message.answer(text, parse_mode="Markdown", reply_markup=get_template_keyboard(page=1))


@router.callback_query(F.data == "tpl_page_2")
async def template_page_2(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=get_template_keyboard(page=2))
    except Exception:
        pass


@router.callback_query(F.data == "tpl_page_1")
async def template_page_1(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=get_template_keyboard(page=1))
    except Exception:
        pass



@router.callback_query(F.data == "help_menu")
async def help_menu(callback: CallbackQuery):
    await callback.answer()
    photo = FSInputFile(HELP_IMAGE)
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=photo,
                caption=HELP_TEXT,
                parse_mode="Markdown"
            ),
            reply_markup=get_help_keyboard()
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        try:
            await callback.message.answer_photo(
                photo=photo,
                caption=HELP_TEXT,
                parse_mode="Markdown",
                reply_markup=get_help_keyboard()
            )
        except Exception:
            await callback.message.answer(HELP_TEXT, parse_mode="Markdown", reply_markup=get_help_keyboard())

    await _send_help_example(callback.message)


@router.message(Command("help"))
async def cmd_help(message: Message):
    photo = FSInputFile(HELP_IMAGE)
    try:
        await message.answer_photo(photo=photo, caption=HELP_TEXT, parse_mode="Markdown", reply_markup=get_help_keyboard())
    except Exception:
        await message.answer(HELP_TEXT, parse_mode="Markdown", reply_markup=get_help_keyboard())

    await _send_help_example(message)




@router.message(Command("create"))
async def cmd_create(message: Message, state: FSMContext):
    """Start the builder via command — goes straight to template selection."""
    await state.clear()
    text = (
        "📄 *Choose a Template*\n\n"
        "Pick a style to start your website.\n"
        "_Tip: tap More ▶ for more templates._"
    )
    photo = FSInputFile(TEMPLATE_IMAGE)
    try:
        await message.answer_photo(
            photo=photo,
            caption=text,
            parse_mode="Markdown",
            reply_markup=get_template_keyboard(page=1)
        )
    except Exception:
        await message.answer(text, parse_mode="Markdown", reply_markup=get_template_keyboard(page=1))


@router.callback_query(F.data.startswith("tpl_"))
async def use_template(callback: CallbackQuery, state: FSMContext):
    """Start builder with a pre-applied style preset from template selection."""
    from utils.styles import STYLE_PRESETS
    from utils.states import SECTIONS, SECTION_META
    from handlers.memebuilder import show_hub
    
    preset_key = callback.data.replace("tpl_", "")
    if preset_key not in STYLE_PRESETS:
        await callback.answer("Unknown template", show_alert=True)
        return
    
    await callback.answer()
    
    # Initialize site_data with the chosen style applied to all sections
    preset = STYLE_PRESETS[preset_key].copy()
    preset.pop("name", None)
    
    data = await state.get_data()
    site_data = data.get("site_data", {})
    
    for sec in SECTIONS:
        if sec not in site_data:
            site_data[sec] = {}
        
        # Preserve existing content, otherwise use defaults
        existing_content = site_data[sec].get("content", {})
        if not existing_content:
            site_data[sec]["content"] = SECTION_META[sec].get("defaults", {}).copy()
        
        # Apply the new style to the section
        site_data[sec]["style"] = preset.copy()
    
    await state.update_data(site_data=site_data, template="memecoin")
    
    preset_name = STYLE_PRESETS[preset_key]["name"]
    log_activity(callback.from_user.id, "template_chosen", preset_name)
    
    await callback.message.answer(
        f"🎨 Template **{preset_name}** loaded!\n\n"
        "Now edit each section's content:",
        parse_mode="Markdown"
    )
    await show_hub(callback.message, state)


