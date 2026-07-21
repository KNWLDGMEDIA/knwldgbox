import asyncio
import json
from fastapi import WebSocket, APIRouter
import re
import os

# Prevent black console windows from flashing on Windows when spawning subprocesses
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

router = APIRouter()

from config import MAIGRET_DIR
REPORTS_DIR = str(MAIGRET_DIR)

# Regex to strip ANSI escape sequences from subprocess output
ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class MaigretService:
    async def handle_websocket(self, websocket: WebSocket):
        await websocket.accept()
        process = None

        try:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action")
            username = payload.get("username", "").strip()
            timeout = payload.get("timeout", 10)
            all_sites = payload.get("allSites", False)

            if action != "search" or not username:
                await websocket.send_json({"type": "error", "text": "Invalid request"})
                return

            # Sanitize username to prevent command injection
            username = "".join(c for c in username if c.isalnum() or c in "_-.")
            
            cmd_args = [
                "maigret", username,
                "--json", "ndjson",
                "--no-progressbar",
                "--folder", REPORTS_DIR,
                "--timeout", str(timeout)
            ]
            
            if all_sites:
                cmd_args.append("--all-sites")

            # Execute maigret with --no-progressbar to avoid \r flooding
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024,  # 1 MB buffer limit
                creationflags=CREATE_NO_WINDOW,
            )

            current_site = None
            last_progress = -1

            # Read stdout line by line (safe now that progress bar is disabled)
            while True:
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=120)
                except asyncio.TimeoutError:
                    await websocket.send_json({"type": "info", "text": "Still scanning..."})
                    continue

                if not line:
                    break

                text = line.decode("utf-8", errors="ignore").strip()
                if not text:
                    continue

                # Strip ANSI escape codes
                text = ANSI_RE.sub("", text)

                if "[+]" in text:
                    text = text[text.find("[+]"):]
                    parts = text[4:].split(": http", 1)
                    if len(parts) == 2:
                        site = parts[0].strip()
                        url = "http" + parts[1].strip()
                        current_site = site
                        await websocket.send_json({
                            "type": "found",
                            "site": site,
                            "url": url,
                        })
                    else:
                        await websocket.send_json({"type": "info", "text": text})

                elif text.startswith(("├─", "└─")) and current_site:
                    key_val = text.lstrip("├└─ ").split(":", 1)
                    if len(key_val) == 2:
                        key = key_val[0].strip()
                        val = key_val[1].strip()
                        if key.startswith("_"):
                            continue  # Skip internal fields
                        await websocket.send_json({
                            "type": "tag",
                            "site": current_site,
                            "key": key,
                            "value": val,
                        })

                elif "Searching" in text:
                    progress_match = re.search(r"\[(\d+)%\]", text)
                    if progress_match:
                        pct = int(progress_match.group(1))
                        if pct - last_progress >= 5:
                            last_progress = pct
                            await websocket.send_json({"type": "progress", "percent": pct})

            await process.wait()

            # Attempt to read the ndjson report for enriched data
            report_path = os.path.join(REPORTS_DIR, f"report_{username}_ndjson.json")
            if os.path.exists(report_path):
                try:
                    with open(report_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            entry = json.loads(line)
                            if entry.get("status") and entry["status"].get("status") == "Claimed":
                                site_name = entry.get("siteName", "")
                                ids = entry.get("status", {}).get("ids", {})
                                if ids:
                                    await websocket.send_json({
                                        "type": "enrich",
                                        "site": site_name,
                                        "ids": ids,
                                    })
                except Exception:
                    pass

            await websocket.send_json({"type": "done"})

        except Exception as e:
            try:
                await websocket.send_json({"type": "error", "text": str(e)})
            except Exception:
                pass
        finally:
            if process and process.returncode is None:
                process.terminate()


maigret_service = MaigretService()


@router.websocket("/ws/maigret")
async def maigret_ws(websocket: WebSocket):
    await maigret_service.handle_websocket(websocket)
