import asyncio
import json
import os
import sys
import re
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# Prevent black console windows from flashing on Windows when spawning subprocesses
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

router = APIRouter()

from config import TIKTOK_DIR as DATA_DIR

@router.websocket("/ws/tiktok")
async def tiktok_hashtag_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    process = None
    try:
        data = await websocket.receive_text()
        request = json.loads(data)
        action = request.get("action")
        hashtag = request.get("hashtag", "").strip()
        limit = request.get("limit", 20)
        topN = request.get("topN", 20)
        
        if action == "analyze" and hashtag:
            if not hashtag.isalnum():
                await websocket.send_json({"type": "error", "text": "Invalid hashtag format"})
                return

            await websocket.send_json({"type": "info", "text": "Checking browser dependencies (may download Chromium on first run)..."})
            install_cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
            install_proc = await asyncio.create_subprocess_exec(
                *install_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW,
            )
            await install_proc.wait()

            cmd = [
                "tiktok-hashtag-analysis", 
                hashtag, 
                "--number", str(topN), 
                "--table", 
                "--limit", str(limit)
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW,
            )

            await websocket.send_json({"type": "info", "text": f"Initializing TikTok scraper for #{hashtag}..."})

            in_table = False
            results = []

            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                text = line.decode('utf-8', errors='ignore').strip()
                if not text:
                    continue

                if "Hashtags to scrape" in text:
                    await websocket.send_json({"type": "info", "text": "Bypassing anti-bot protection (this may take a moment)..."})
                elif "Scraped" in text and "posts containing" in text:
                    await websocket.send_json({"type": "info", "text": text})
                elif "WARNING" in text or "Encountered error" in text:
                    await websocket.send_json({"type": "info", "text": f"⚠️ {text}"})
                elif "Co-occurring hashtags" in text:
                    in_table = True
                    await websocket.send_json({"type": "info", "text": "Parsing co-occurring hashtags..."})
                elif in_table and "Total posts:" in text:
                    in_table = False
                elif in_table:
                    # Strip ANSI color codes
                    clean_text = ansi_escape.sub('', text)
                    # Replace common table border characters with spaces
                    clean_text = clean_text.replace('│', ' ').replace('|', ' ').strip()
                    
                    # Parse the table row
                    parts = clean_text.split()
                    if len(parts) >= 4 and parts[0].isdigit():
                        rank = parts[0]
                        tag = parts[1]
                        occurrences = parts[2]
                        frequency = parts[3]
                        results.append({
                            "rank": rank,
                            "tag": tag,
                            "occurrences": occurrences,
                            "frequency": frequency
                        })
                        await websocket.send_json({"type": "found", "hashtag": tag, "count": occurrences, "freq": frequency})

            await process.wait()
            await websocket.send_json({"type": "done", "total": len(results)})
            
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        await websocket.send_json({"type": "error", "text": str(e)})
    finally:
        if process and process.returncode is None:
            try:
                process.terminate()
            except Exception:
                pass
