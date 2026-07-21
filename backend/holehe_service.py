import asyncio
import json
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from config import tool_path

# Prevent black console windows from flashing on Windows when spawning subprocesses
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

router = APIRouter()

@router.websocket("/ws/holehe")
async def holehe_websocket(websocket: WebSocket):
    await websocket.accept()
    process = None
    try:
        data = await websocket.receive_text()
        request = json.loads(data)
        
        if request.get('action') == 'search':
            email = request.get('email')
            if not email:
                await websocket.send_text(json.dumps({"type": "error", "text": "No email provided."}))
                return

            stealth_mode = request.get('stealthMode', False)
            
            await websocket.send_text(json.dumps({"type": "info", "text": f"Starting Holehe on {email}..."}))
            
            # Build command arguments
            cmd_args = [tool_path("holehe"), email, "--only-used", "--no-color", "--no-clear"]
            if stealth_mode:
                cmd_args.append("-NP")
            
            # Run holehe with unbuffered output
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=CREATE_NO_WINDOW,
            )
            
            # Read stdout line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                decoded_line = line.decode('utf-8', errors='replace').strip()
                
                if decoded_line.startswith("[+] "):
                    site_raw = decoded_line.replace("[+] ", "").strip()
                    
                    if site_raw.startswith("Email used,"):
                        continue
                        
                    site_name = site_raw
                    url = None
                    extra_info = None
                    
                    if " / " in site_raw:
                        parts = site_raw.split(" / ")
                        site_name = parts[0].strip()
                        if parts[-1].strip().startswith("http"):
                            url = parts[-1].strip()
                            extra_info = " / ".join(parts[1:-1])
                        else:
                            extra_info = " / ".join(parts[1:])
                    
                    if site_name and site_name not in ["amazon.com"]:
                        await websocket.send_text(json.dumps({
                            "type": "found", 
                            "site": site_name,
                            "url": url,
                            "extra": extra_info
                        }))
            
            await process.wait()
            await websocket.send_text(json.dumps({"type": "done"}))
            
    except WebSocketDisconnect:
        if process and process.returncode is None:
            process.terminate()
    except Exception as e:
        await websocket.send_text(json.dumps({"type": "error", "text": str(e)}))
        if process and process.returncode is None:
            process.terminate()
