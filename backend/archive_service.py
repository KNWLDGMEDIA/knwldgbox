import nodriver as uc
import asyncio
import base64
from fastapi import APIRouter
from pydantic import BaseModel
import os
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse
import time

# Prevent black console windows from flashing on Windows when spawning subprocesses
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

router = APIRouter()


def _find_playwright_chromium() -> str | None:
    """Locate the Chromium binary downloaded by Playwright, if any."""
    bases = []
    env_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if env_path:
        bases.append(Path(env_path))
    if os.name == "nt":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            bases.append(Path(local_appdata) / "ms-playwright")
    else:
        bases.append(Path.home() / ".cache" / "ms-playwright")
        bases.append(Path.home() / "Library" / "Caches" / "ms-playwright")

    exe_rel = Path("chrome-win") / "chrome.exe" if os.name == "nt" else Path("chrome-linux") / "chrome"
    for base in bases:
        if not base.is_dir():
            continue
        # Newest revision first
        for chromium_dir in sorted(base.glob("chromium-*"), reverse=True):
            exe = chromium_dir / exe_rel
            if exe.exists():
                return str(exe)
    return None


async def _install_playwright_chromium():
    """Download Playwright's Chromium (first run on machines without Chrome)."""
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "playwright", "install", "chromium",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    await process.wait()


async def _start_browser():
    """
    Start a headless browser. Prefers the system Chrome/Chromium; falls back to
    Playwright's Chromium (downloading it on first use if necessary).
    """
    try:
        return await uc.start(headless=True)
    except Exception:
        pass  # No usable system browser — try Playwright's Chromium below

    exe = _find_playwright_chromium()
    if not exe:
        await _install_playwright_chromium()
        exe = _find_playwright_chromium()

    if exe:
        return await uc.start(headless=True, browser_executable_path=exe)

    raise RuntimeError(
        "No Chrome/Chromium browser found. Install Google Chrome, "
        "or run 'python -m playwright install chromium' once."
    )

class ArchiveRequest(BaseModel):
    url: str

from config import ARCHIVES_DIR

@router.post("/api/archive")
async def archive_url_endpoint(req: ArchiveRequest):
    url = req.url
    
    # Security check: Prevent SSRF (local file reads, internal network scans)
    if not url.startswith(("http://", "https://")):
        return {"status": "error", "detail": "Only HTTP/HTTPS URLs are allowed."}
        
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if hostname in ["localhost", "127.0.0.1", "0.0.0.0", "::1"] or hostname.startswith(("192.168.", "10.", "172.16.")):
        return {"status": "error", "detail": "Internal or local IPs are not allowed."}

    # Format a safe filename based on the domain
    domain = parsed.netloc if parsed.netloc else parsed.path.replace('/', '_')
    domain = domain.replace(":", "_")
    timestamp = int(time.time())
    archive_id = f"{domain}_{timestamp}_{uuid.uuid4().hex[:6]}"
    
    archive_path_base = os.path.join(ARCHIVES_DIR, archive_id)
    pdf_path = f"{archive_path_base}.pdf"
    png_path = f"{archive_path_base}.png"

    try:
        # Launch chromium (system browser, or Playwright's as fallback)
        browser = await _start_browser()
        
        try:
            # Go to URL
            page = await browser.get(url)
            
            # Wait an extra 3 seconds for dynamic JS elements (like images or tweets) to render fully
            await asyncio.sleep(3)
            
            # Save PDF (print_background ensures CSS colors/images are rendered)
            result = await page.send(uc.cdp.page.print_to_pdf(print_background=True))
            pdf_data = base64.b64decode(result[0])
            with open(pdf_path, 'wb') as f:
                f.write(pdf_data)
            
            # Save Full Page Screenshot
            await page.save_screenshot(png_path, full_page=True)
        finally:
            browser.stop()
            
        return {
            "status": "success",
            "archive_id": archive_id,
            "url": url,
            "pdf_file": f"{archive_id}.pdf",
            "png_file": f"{archive_id}.png",
            "timestamp": timestamp
        }
    except Exception as e:
        return {
            "status": "error",
            "detail": str(e)
        }

@router.get("/api/archives")
def get_archives():
    if not os.path.exists(ARCHIVES_DIR):
        return []
    
    files = os.listdir(ARCHIVES_DIR)
    archives = {}
    
    for f in files:
        if f.endswith('.pdf') or f.endswith('.png'):
            archive_id = f.rsplit('.', 1)[0]
            if archive_id not in archives:
                archives[archive_id] = {
                    "archive_id": archive_id,
                    "pdf_file": None,
                    "png_file": None
                }
            if f.endswith('.pdf'):
                archives[archive_id]["pdf_file"] = f
            elif f.endswith('.png'):
                archives[archive_id]["png_file"] = f
                
    return list(archives.values())

@router.delete("/api/archives/{archive_id}")
def delete_archive_endpoint(archive_id: str):
    pdf_path = os.path.join(ARCHIVES_DIR, f"{archive_id}.pdf")
    png_path = os.path.join(ARCHIVES_DIR, f"{archive_id}.png")
    
    deleted = False
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
        deleted = True
    if os.path.exists(png_path):
        os.remove(png_path)
        deleted = True
        
    return {"success": deleted}

