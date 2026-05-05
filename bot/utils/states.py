from aiogram.fsm.state import State, StatesGroup


class BuilderState(StatesGroup):
    """Simplified FSM — one state per action, not per field."""

    # Content input — user sends ONE message with all fields
    editing_content = State()

    # Style input — user sends colors or picks preset
    editing_style = State()

    # Payment
    tx_hash = State()


# ─── Section Registry ───
SECTIONS = [
    "header",
    "hero",
    "about",
    "tokenomics",
    "roadmap",
    "buy",
    "socials",
    "footer",
]

SECTION_META = {
    "header": {
        "emoji": "🔷",
        "label": "Header",
        "content_prompt": (
            "🔷 **HEADER — Edit Content**\n\n"
            "📸 **Upload your coin logo image** (auto-fills the entire site!)\n\n"
            "⚠️ **IMPORTANT TIP FOR TRANSPARENCY:** ⚠️\n"
            "Telegram automatically adds white/black backgrounds to photos. To keep your logo background transparent, upload the image **as a File / Document** (📎 -> File), NOT as a standard photo!\n\n"
            "Just send the file, or send it with a caption:\n"
            "```\n"
            "Logo: YourCoinName\n"
            "Links: Home, About, Buy, Tokenomics\n"
            "```\n\n"
            "Or type `skip` to use defaults."
        ),
        "content_fields": ["logo", "links", "logo_image"],
        "defaults": {"logo": "MEME COIN", "links": "Home, About, Buy, Tokenomics", "logo_image": ""},
    },
    "hero": {
        "emoji": "🦸",
        "label": "Hero",
        "content_prompt": (
            "🦸 **HERO — Edit Content**\n\n"
            "Send text or upload image (caption optional):\n"
            "```\n"
            "Title: $MEMCO Future of Meme Coins\n"
            "Subtitle: To the moon 🚀\n"
            "Button: Buy Now\n"
            "Link: https://dex.example.com\n"
            "Contract: 0xABC123...\n"
            "```\n\n"
            "Image field: `Hero Image` (upload photo to replace hero mascot)\n\n"
            "Or type `skip` to use defaults."
        ),
        "content_fields": ["title", "subtitle", "button", "link", "contract", "hero_image"],
        "defaults": {
            "title": "$MEME Future of Meme Coins",
            "subtitle": "To the moon 🚀",
            "button": "Buy Now",
            "link": "#",
            "contract": "0x0000000000000000000000000000000000000000",
            "hero_image": "",
        },
    },
    "about": {
        "emoji": "📖",
        "label": "About / Lore",
        "content_prompt": (
            "📖 **ABOUT — Edit Content**\n\n"
            "Send text or upload image (caption optional):\n"
            "```\n"
            "Title: About Us\n"
            "Text: Your project story here...\n"
            "```\n\n"
            "Image field: `About Image`\n\n"
            "Or type `skip` to use defaults."
        ),
        "content_fields": ["title", "text", "about_image"],
        "defaults": {
            "title": "About Us",
            "text": "Born from the love of memes and the power of community, we are building an ecosystem where everyone has a voice.",
            "about_image": "",
        },
    },
    "tokenomics": {
        "emoji": "📊",
        "label": "Tokenomics",
        "content_prompt": (
            "📊 **TOKENOMICS — Edit Content**\n\n"
            "Send text or upload image (caption optional):\n"
            "```\n"
            "Supply: 420.69T\n"
            "Tax: 0/0\n"
            "Burn: 2%\n"
            "Liquidity: Locked\n"
            "```\n\n"
            "Image field: `Tokenomics Image`\n\n"
            "Or type `skip` to use defaults."
        ),
        "content_fields": ["supply", "tax", "burn", "liquidity", "tokenomics_image"],
        "defaults": {
            "supply": "420.69T",
            "tax": "0/0",
            "burn": "N/A",
            "liquidity": "Locked",
            "tokenomics_image": "",
        },
    },
    "roadmap": {
        "emoji": "🗺️",
        "label": "Roadmap",
        "content_prompt": (
            "🗺️ **ROADMAP — Edit Content**\n\n"
            "Send ONE message with phases (one per line):\n"
            "```\n"
            "Phase 1: Launch & Community Building\n"
            "Phase 2: CEX Listings & Partnerships\n"
            "Phase 3: Ecosystem Expansion\n"
            "```\n\n"
            "Or type `skip` to use defaults."
        ),
        "content_fields": ["phases"],
        "defaults": {
            "phases": "Phase 1: Launch & Community\nPhase 2: DEX & CEX Listings\nPhase 3: Ecosystem Growth"
        },
    },
    "buy": {
        "emoji": "🛒",
        "label": "How to Buy",
        "content_prompt": (
            "🛒 **HOW TO BUY — Edit Content**\n\n"
            "Send steps text and/or upload images:\n"
            "```\n"
            "Step 1: Create a Wallet\n"
            "Step 2: Get some ETH/BNB\n"
            "Step 3: Go to DEX\n"
            "Step 4: Swap for Tokens\n"
            "Button: Buy on PancakeSwap\n"
            "```\n\n"
            "Image fields: `Buy Step 1 Image`, `Buy Step 2 Image`, `Buy Step 3 Image`\n"
            "Tip: upload image with caption `Field: buy_step_2_image` to target a step.\n\n"
            "Or type `skip` to use defaults."
        ),
        "content_fields": ["steps", "button", "buy_step_1_image", "buy_step_2_image", "buy_step_3_image"],
        "defaults": {
            "steps": "Create a Wallet\nGet some ETH/BNB\nGo to DEX\nSwap for Tokens",
            "button": "Buy on DEX",
            "buy_step_1_image": "",
            "buy_step_2_image": "",
            "buy_step_3_image": "",
        },
    },
    "socials": {
        "emoji": "💬",
        "label": "Socials",
        "content_prompt": (
            "💬 **SOCIALS — Edit Content**\n\n"
            "Send ONE message with links for any platform you want to enable:\n"
            "```\n"
            "Telegram: https://t.me/yourcoin\n"
            "Twitter: https://x.com/yourcoin\n"
            "Discord: https://discord.gg/yourcoin\n"
            "Instagram: https://instagram.com/yourcoin\n"
            "TikTok: https://tiktok.com/@yourcoin\n"
            "Facebook: https://facebook.com/yourcoin\n"
            "Reddit: https://reddit.com/r/yourcoin\n"
            "Binance: https://binance.com/...\n"
            "DexScreener: https://dexscreener.com/...\n"
            "```\n\n"
            "Or type `skip` to use defaults."
        ),
        "content_fields": ["telegram", "twitter", "discord", "instagram", "tiktok", "facebook", "reddit", "binance", "dexscreener"],
        "defaults": {"telegram": "#", "twitter": "#", "discord": "#", "instagram": "", "tiktok": "", "facebook": "", "reddit": "", "binance": "", "dexscreener": ""},
    },
    "footer": {
        "emoji": "🔻",
        "label": "Footer",
        "content_prompt": (
            "🔻 **FOOTER — Edit Content**\n\n"
            "Send ONE message with:\n"
            "```\n"
            "Text: © 2026 MyCoin. All rights reserved.\n"
            "```\n\n"
            "Or type `skip` to use defaults."
        ),
        "content_fields": ["text"],
        "defaults": {"text": "© 2026 Meme Coin. All rights reserved. Not financial advice."},
    },
}
