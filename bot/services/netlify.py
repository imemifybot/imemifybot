import aiohttp
import os
import zipfile
import io
import time
from dotenv import load_dotenv

# Load env variables strictly from bot/.env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# Only use the first token
NETLIFY_ACCESS_TOKEN = os.getenv("NETLIFY_ACCESS_TOKEN_1") or os.getenv("NETLIFY_ACCESS_TOKEN")

async def deploy_to_netlify(html_content: str, project_name: str) -> str:
    """
    Deploys a single HTML string as index.html to Netlify via a zip upload.
    Returns the site URL if successful, otherwise raises an exception.
    """
    if not NETLIFY_ACCESS_TOKEN:
        raise ValueError("NETLIFY_ACCESS_TOKEN_1 is not set in .env")

    # Create a zip file in memory containing the index.html inside a directory.
    # Netlify requires the file to be inside a directory in the zip to render HTML properly.
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        # Set proper file permissions just in case
        info = zipfile.ZipInfo("site/index.html", date_time=time.localtime()[:6])
        info.external_attr = 0o644 << 16
        zip_file.writestr(info, html_content)

    zip_buffer.seek(0)
    
    headers = {
        "Authorization": f"Bearer {NETLIFY_ACCESS_TOKEN}",
        "Content-Type": "application/zip",
    }
    
    url = "https://api.netlify.com/api/v1/sites"
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Create a site or deploy directly
        async with session.post(url, headers=headers, data=zip_buffer.read()) as response:
            if response.status not in (200, 201):
                error_text = await response.text()
                raise Exception(f"Netlify API Error {response.status}: {error_text}")
            
            data = await response.json()
            site_url = data.get("ssl_url") or data.get("url")
            
            # Ensure it is https
            if site_url and site_url.startswith("http://"):
                site_url = site_url.replace("http://", "https://", 1)
            
            if not site_url:
                raise Exception("Netlify API did not return a site URL.")
                
            return site_url
