"""
Parse single-message content input into structured data.
Handles the "Key: Value" format sent by users.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Keys that appear in the buy-section prompt but are NOT step descriptions
NON_STEP_KEYS = {"button", "btn", "link", "url", "contract", "field"}


def parse_content_input(text: str, section: str, fields: list) -> dict:
    """
    Parse a multi-line "Key: Value" message into a dict.
    
    Input example:
        Title: My Coin
        Subtitle: To the moon
        Button: Buy Now
    
    Returns: {"title": "My Coin", "subtitle": "To the moon", "button": "Buy Now"}
    """
    result = {}
    
    # Normalize field names for matching
    field_lower = {f.lower(): f for f in fields}
    
    # Special handling for sections with multi-line content
    if section == "roadmap":
        # Each line that doesn't match "Key:" format is a phase
        phases = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            phases.append(line)
        if phases:
            result["phases"] = "\n".join(phases)
        return result
    
    if section == "buy":
        # Lines starting with Step or numbers are steps, "Button:" is button
        steps = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                key_clean = key.strip().lower()
                if key_clean in {"button", "btn"}:
                    result["button"] = val.strip()
                    continue
                # Skip non-step labelled lines (Link:, URL:, Contract:, Field:...)
                if key_clean in NON_STEP_KEYS:
                    continue
            # Everything else is a step
            # Strip leading "Step N:" or "N." or "N:" prefix
            cleaned = re.sub(r'^(step\s*\d+[:.]\s*|\d+[.):\s]+)', '', line, flags=re.IGNORECASE).strip()
            if cleaned:
                steps.append(cleaned)
        if steps:
            result["steps"] = "\n".join(steps)
        return result

    # General key:value parsing
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        
        key, val = line.split(":", 1)
        key_clean = key.strip().lower()
        val_raw = val.strip()

        # Skip bare URL lines (e.g. "https://t.me/...") — key would be "http" or "https"
        if key_clean in ("http", "https"):
            continue

        # Reassemble value in case it contained colons (e.g. full URL after key:)
        # val already has everything after the first colon, which is correct.
        val = val_raw
        
        if not val:
            continue
        
        # Try exact match
        if key_clean in field_lower:
            result[field_lower[key_clean]] = val
            continue
        
        # Try partial match
        for field_key in field_lower:
            if field_key in key_clean or key_clean in field_key:
                result[field_lower[field_key]] = val
                break
    
    return result


def format_section_summary(section: str, content: dict, style: dict) -> str:
    """Format a section's data for display in Telegram."""
    if not content and not style:
        return "❌ _Not configured_"
    
    lines = []

    # Special pretty display for the socials section
    if section == "socials" and content:
        SOCIAL_ICONS = {
            "telegram":    "✈️  Telegram",
            "twitter":     "🐦  X/Twitter",
            "discord":     "👾  Discord",
            "instagram":   "📸  Instagram",
            "tiktok":      "🎵  TikTok",
            "facebook":    "📘  Facebook",
            "reddit":      "🤖  Reddit",
            "binance":     "🟡  Binance",
            "dexscreener": "📊  DexScreener",
        }
        set_count = 0
        for key, label in SOCIAL_ICONS.items():
            val = content.get(key, "")
            if val and val != "#":
                url_display = val[:40] + "..." if len(val) > 40 else val
                lines.append(f"  ✅ {label}: `{url_display}`")
                set_count += 1
            else:
                lines.append(f"  ⬜ {label}")
        if not set_count:
            lines.append("_No social links set yet._")
        if style:
            bg = style.get("bg_color", "")
            acc = style.get("accent_color", "")
            if bg or acc:
                lines.append(f"\n  🎨 {bg} {acc}".strip())
        return "\n".join(lines)

    if content:
        for key, val in content.items():
            display_val = str(val)
            if key.endswith("_image") and display_val.startswith("data:image/"):
                display_val = "[uploaded image]"
            if len(display_val) > 60:
                display_val = display_val[:57] + "..."
            clean_key = key.replace("_", " ").title()
            lines.append(f"  • {clean_key}: `{display_val}`")
    
    if style:
        style_parts = []
        if style.get("bg_color"):
            style_parts.append(style["bg_color"])
        if style.get("accent_color"):
            style_parts.append(style["accent_color"])
        if style.get("button_style"):
            style_parts.append(style["button_style"])
        if style_parts:
            lines.append(f"  🎨 {', '.join(style_parts)}")
    
    return "\n".join(lines) if lines else "✅ _Using defaults_"
