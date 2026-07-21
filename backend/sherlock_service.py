import asyncio
import json
import os
from fastapi import WebSocket

# Prevent black console windows from flashing on Windows when spawning subprocesses
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

class SherlockService:
    async def handle_websocket(self, websocket: WebSocket):
        await websocket.accept()
        process = None
        
        try:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action")
            username = payload.get("username")
            timeout = payload.get("timeout", 60)
            
            if action == "search" and username:
                # Sanitize username
                username = "".join(c for c in username if c.isalnum() or c in "_-")
                
                # Execute sherlock
                process = await asyncio.create_subprocess_exec(
                    "sherlock", username, "--print-found", "--timeout", str(timeout),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    creationflags=CREATE_NO_WINDOW,
                )
                
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                        
                    text = line.decode('utf-8').strip()
                    if text:
                        if text.startswith("[+]"):
                            # Parse "[+] Site: URL"
                            parts = text[4:].split(": http", 1)
                            if len(parts) == 2:
                                site = parts[0].strip()
                                url = "http" + parts[1].strip()
                                await websocket.send_json({"type": "found", "site": site, "url": url})
                            else:
                                await websocket.send_json({"type": "log", "text": text})
                        elif text.startswith("[*]"):
                            await websocket.send_json({"type": "info", "text": text})
                        else:
                            await websocket.send_json({"type": "log", "text": text})
                            
                await process.wait()
                await websocket.send_json({"type": "done"})
        except Exception as e:
            try:
                await websocket.send_json({"type": "error", "text": str(e)})
            except Exception:
                pass
        finally:
            if process and process.returncode is None:
                process.terminate()

sherlock_service = SherlockService()
