import os
import sys
import json
import asyncio
import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Prevent black console windows from flashing on Windows when spawning subprocesses
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

from ghunt.helpers.utils import get_httpx_client
from ghunt.helpers import auth
from ghunt.objects.base import GHuntCreds
from ghunt.errors import GHuntInvalidSession

router = APIRouter()

class GHuntPayload(BaseModel):
    email: str

class GHuntLoginPayload(BaseModel):
    b64_token: str

@router.post("/api/ghunt/email")
async def scan_ghunt_email(payload: GHuntPayload):
    email = payload.email.strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    wrapper_path = os.path.join(os.path.dirname(__file__), "ghunt_wrapper.py")
    
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable, wrapper_path, email,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
        )
        stdout, stderr = await process.communicate()
        stdout_str = stdout.decode('utf-8')
        stderr_str = stderr.decode('utf-8')
        
        if process.returncode != 0:
            if "GHuntInvalidSession" in stderr_str or "login" in stderr_str:
                raise HTTPException(
                    status_code=401, 
                    detail="auth_required"
                )
            raise HTTPException(status_code=500, detail=f"unknown: {stderr_str}")

        if "GHUNT_ERROR_START" in stdout_str:
            err_msg = stdout_str.split("GHUNT_ERROR_START")[1].split("GHUNT_ERROR_END")[0].strip()
            raise HTTPException(status_code=400, detail=err_msg)

        if "GHUNT_JSON_START" in stdout_str:
            json_str = stdout_str.split("GHUNT_JSON_START")[1].split("GHUNT_JSON_END")[0].strip()
            data = json.loads(json_str)
            return {"status": "success", "data": data}

        raise HTTPException(status_code=500, detail="unknown: Failed to parse GHunt JSON output from wrapper.")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/ghunt/login")
async def ghunt_login(payload: GHuntLoginPayload):
    if not payload.b64_token:
        raise HTTPException(status_code=400, detail="invalid_token")

    try:
        try:
            data = json.loads(base64.b64decode(payload.b64_token))
        except Exception:
            raise HTTPException(status_code=400, detail="invalid_token")
            
        oauth_token = data.get("oauth_token")
        if not oauth_token:
            raise HTTPException(status_code=400, detail="invalid_token")
            
        as_client = get_httpx_client()
        try:
            master_token, services, owner_email, owner_name = await auth.android_master_auth(as_client, oauth_token)
            
            ghunt_creds = GHuntCreds()
            ghunt_creds.android.master_token = master_token
            ghunt_creds.cookies = {"a": "a"} # Dummy
            ghunt_creds.osids = {"a": "a"} # Dummy
            
            await auth.gen_cookies_and_osids(as_client, ghunt_creds)
            ghunt_creds.save_creds()
        finally:
            await as_client.aclose()
            
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"unknown: {str(e)}")

@router.get("/api/ghunt/status")
async def ghunt_status():
    creds = GHuntCreds()
    try:
        creds.load_creds()
        # Basic check to see if cookies and tokens exist
        if not creds.cookies or not creds.android.master_token:
            return {"authenticated": False}
        return {"authenticated": True}
    except GHuntInvalidSession:
        return {"authenticated": False}
    except Exception as e:
        # If the file doesn't exist or is corrupted, it's not authenticated
        return {"authenticated": False}
