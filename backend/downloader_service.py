import asyncio
import json
import os
import platform
import subprocess
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from config import DOWNLOADS_DIR

# Prevent black console windows from flashing on Windows when spawning subprocesses
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

router = APIRouter()

@router.get("/api/downloads/file/{filename}")
def download_file(filename: str):
    file_path = DOWNLOADS_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        return {"status": "error", "message": "File not found"}
    return FileResponse(path=file_path, filename=filename)

@router.get("/api/downloads/list")
def list_downloads():
    if not DOWNLOADS_DIR.exists():
        return {"status": "success", "data": []}
        
    files = []
    for f in DOWNLOADS_DIR.iterdir():
        if f.is_file() and not f.name.endswith(".part") and not f.name.endswith(".ytdl"):
            stat = f.stat()
            files.append({
                "name": f.name,
                "size": stat.st_size,
                "time": stat.st_mtime
            })
    files.sort(key=lambda x: x["time"], reverse=True)
    return {"status": "success", "data": files}

@router.post("/api/downloads/open")
def open_downloads_dir():
    if os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"):
        return {"status": "error", "message": "Cannot open file explorer from inside a container. Your files are located in ~/Downloads/KNWLDGBox on your host machine."}
    try:
        if platform.system() == "Windows":
            os.startfile(str(DOWNLOADS_DIR))
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(DOWNLOADS_DIR)], creationflags=CREATE_NO_WINDOW)
        else:
            subprocess.Popen(["xdg-open", str(DOWNLOADS_DIR)], creationflags=CREATE_NO_WINDOW)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.websocket("/ws/downloader")
async def downloader_ws(websocket: WebSocket):
    await websocket.accept()
    process = None
    
    try:
        data = await websocket.receive_text()
        request = json.loads(data)
        action = request.get("action")
        url = request.get("url", "").strip()
        cookies_browser = request.get("cookies", "none")
        download_format = request.get("format", "best")
        
        if action == "download" and url:
            if not url.startswith(("http://", "https://")):
                await websocket.send_json({"type": "error", "text": "Only HTTP/HTTPS URLs are allowed."})
                return
            
            output_template = str(DOWNLOADS_DIR / "%(title)s.%(ext)s")
            
            cmd = [
                "yt-dlp",
                "--newline",
                "--no-playlist",
                "-o", output_template
            ]

            if cookies_browser and cookies_browser != "none":
                cmd.extend(["--cookies-from-browser", cookies_browser])

            if download_format == "audio":
                cmd.extend(["-x", "--audio-format", "mp3"])

            cmd.append(url)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW,
            )
            
            await websocket.send_json({"type": "info", "text": f"Initializing download for {url}..."})
            
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                text = line.decode('utf-8', errors='ignore').strip()
                if not text:
                    continue
                
                # Try to parse progress from yt-dlp output
                if "[download]" in text and "%" in text:
                    # Example: [download]  10.0% of  50.00MiB at    1.00MiB/s ETA 00:45
                    await websocket.send_json({"type": "progress", "text": text})
                else:
                    await websocket.send_json({"type": "info", "text": text})
                    
            await process.wait()
            
            if process.returncode == 0:
                await websocket.send_json({"type": "done", "text": "Download complete!"})
            else:
                await websocket.send_json({"type": "error", "text": "Download failed. Please check the logs."})
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "text": str(e)})
    finally:
        if process and process.returncode is None:
            try:
                process.terminate()
            except Exception:
                pass
