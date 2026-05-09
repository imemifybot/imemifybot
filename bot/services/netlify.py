import aiohttp
import os
import zipfile
import io
import time
from dotenv import load_dotenv

# Load env variables strictly from bot/.env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

NETLIFY_ACCESS_TOKEN_1 = (os.getenv("NETLIFY_ACCESS_TOKEN_1") or "").strip()
NETLIFY_ACCESS_TOKEN_2 = (os.getenv("NETLIFY_ACCESS_TOKEN_2") or "").strip()
NETLIFY_ACCESS_TOKEN_FALLBACK = (os.getenv("NETLIFY_ACCESS_TOKEN") or "").strip()

def _token_candidates() -> list[str]:
    """
    Return token candidates in priority order.
    - Prefer explicit token 1, then token 2, then legacy NETLIFY_ACCESS_TOKEN.
    """
    tokens: list[str] = []
    for t in (NETLIFY_ACCESS_TOKEN_1, NETLIFY_ACCESS_TOKEN_2, NETLIFY_ACCESS_TOKEN_FALLBACK):
        if t and t not in tokens:
            tokens.append(t)
    return tokens

async def _deploy_with_token(session: aiohttp.ClientSession, token: str, zip_bytes: bytes) -> tuple[int, str, dict]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/zip",
    }
    url = "https://api.netlify.com/api/v1/sites"
    async with session.post(url, headers=headers, data=zip_bytes) as response:
        status = response.status
        text = await response.text()
        data = {}
        try:
            data = await response.json()
        except Exception:
            data = {}
        return status, text, data

async def deploy_to_netlify(html_content: str, project_name: str) -> str:
    """
    Deploys a single HTML string as index.html to Netlify via a zip upload.
    Returns the site URL if successful, otherwise raises an exception.
    """
    tokens = _token_candidates()
    if not tokens:
        raise ValueError("No Netlify access token configured. Set NETLIFY_ACCESS_TOKEN_1 (and optionally _2) in bot/.env.")

    # Create a zip file in memory containing the index.html inside a directory.
    # Netlify requires the file to be inside a directory in the zip to render HTML properly.
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        # Set proper file permissions just in case
        info = zipfile.ZipInfo("site/index.html", date_time=time.localtime()[:6])
        info.external_attr = 0o644 << 16
        zip_file.writestr(info, html_content)

    zip_buffer.seek(0)

    zip_bytes = zip_buffer.read()

    async with aiohttp.ClientSession() as session:
        last_error = None
        for idx, token in enumerate(tokens):
            status, error_text, data = await _deploy_with_token(session, token, zip_bytes)
            if status in (200, 201):
                site_url = (data.get("ssl_url") or data.get("url") or "").strip()
                if site_url.startswith("http://"):
                    site_url = site_url.replace("http://", "https://", 1)
                if not site_url:
                    raise Exception("Netlify API did not return a site URL.")
                return site_url

            # Retry with next token on common auth/rate/limit errors.
            last_error = f"Netlify API Error {status}: {error_text}"
            if status not in (401, 403, 429):
                break
            if idx < len(tokens) - 1:
                continue

        raise Exception(last_error or "Netlify deploy failed.")
