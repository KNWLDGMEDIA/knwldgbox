from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from dotenv import load_dotenv
import feedparser
from config import ENV_FILE, ARCHIVES_DIR
from fastapi.staticfiles import StaticFiles
import os
import json
import base64
import httpx
import time

try:
    from geotext import GeoText
    from geopy.geocoders import Nominatim
    geolocator = Nominatim(user_agent="knwldgbox-osint")
except ImportError:
    GeoText = None
    geolocator = None

geo_cache = {}


try:
    with open(os.path.join(os.path.dirname(__file__), "fr_en_countries.json"), "r", encoding="utf-8") as _f:
        FR_EN_DICT = json.load(_f)
except Exception:
    FR_EN_DICT = {}

from telegram_service import telegram_service
from sherlock_service import sherlock_service
import dataleak_service
import graph_service
import whois_service
import collage_service
import tiktok_service
import ghunt_service
import holehe_service
import maigret_service
import downloader_service
import archive_service
import target_service
import routerClass

obj_class_router = routerClass.routerFunctionPipe("backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(dotenv_path=ENV_FILE, override=True)
    await telegram_service.initialize()
    yield
    await telegram_service.disconnect()


app = FastAPI(title="KNWLDG OSINT Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:8001",
        "http://localhost:8001",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dataleak_service.router)
app.include_router(graph_service.router)
app.include_router(whois_service.router)
app.include_router(collage_service.router)
app.include_router(tiktok_service.router)
app.include_router(ghunt_service.router)
app.include_router(holehe_service.router)
app.include_router(maigret_service.router)
app.include_router(downloader_service.router)
app.include_router(archive_service.router)
app.include_router(target_service.router)

app.mount("/archives", StaticFiles(directory=str(ARCHIVES_DIR)), name="archives")


class SettingsPayload(BaseModel):
    telegram_api_id: str | None = None
    telegram_api_hash: str | None = None
    telegram_phone: str | None = None
    urlscan_api_key: str | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str | None = None
    openrouter_system_prompt: str | None = None

class AuthCodePayload(BaseModel):
    code: str

@app.post("/api/settings")
async def save_settings(payload: SettingsPayload):
    env_content = ""
    if payload.telegram_api_id:
        env_content += f"TG_API_ID={payload.telegram_api_id}\n"
    if payload.telegram_api_hash:
        env_content += f"TG_API_HASH={payload.telegram_api_hash}\n"
    if payload.telegram_phone:
        env_content += f"TG_PHONE={payload.telegram_phone}\n"
    if payload.urlscan_api_key:
        env_content += f"URLSCAN_API_KEY={payload.urlscan_api_key}\n"
    if payload.openrouter_api_key:
        env_content += f"OPENROUTER_API_KEY={payload.openrouter_api_key}\n"
    if payload.openrouter_model:
        env_content += f"OPENROUTER_MODEL={payload.openrouter_model}\n"
    if payload.openrouter_system_prompt is not None:
        encoded = base64.b64encode(payload.openrouter_system_prompt.encode('utf-8')).decode('utf-8')
        env_content += f"OPENROUTER_SYSTEM_PROMPT={encoded}\n"
        
    with open(ENV_FILE, "w") as f:
        f.write(env_content)
        
    
    load_dotenv(dotenv_path=ENV_FILE, override=True)
    return await telegram_service.initialize()

@app.post("/api/telegram/auth/send_code")
async def send_code():
    try:
        return await telegram_service.send_auth_code()
    except Exception as e:
        obj_class_router["utils"]().error_with_reason("Error with Telegram during auth send code!")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/telegram/auth/verify_code")
async def verify_code(payload: AuthCodePayload):
    try:
        return await telegram_service.verify_auth_code(payload.code)
    except ValueError as e:
        obj_class_router["utils"]().error_with_reason("Error with Telegram during auth verify code!")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/extract_locations")
async def extract_locations(payload: dict):
    if not GeoText:
        return {"status": "error", "message": "Geotext or Geopy is missing."}
    
    text = payload.get("text", "")
    if not text:
        return {"status": "success", "locations": []}
    
    
    places = GeoText(text)
    false_positives = {"Ans", "De", "La", "Le", "Les", "Des", "Du", "Un", "Une", "Et", "Sur", "Dans", "Pour", "A", "En", "Or", "Au", "Aux", "Ce", "Ces", "Se", "Me", "Te", "Ne", "Pas", "Qui", "Que", "Qu", "Of", "In", "On", "At", "To", "And", "The", "Is", "Are", "Am", "Be", "Est", "Sont", "Va", "Aller", "Fait", "Non", "Oui"}
    valid_places = [p for p in (places.cities + places.countries) if (len(p) > 2 or p in ["US", "UK"]) and p not in false_positives]
    locations_to_find = list(set(valid_places))
    
    
    text_lower = f" {text.lower()} "
    for fr_term, en_term in FR_EN_DICT.items():
        if f" {fr_term} " in text_lower:
            locations_to_find.append(en_term)
    
    locations_to_find = list(set(locations_to_find))
    
    
    hardcoded_coords = {
        "Gaza Strip": {"lat": 31.4167, "lng": 34.3333},
        "West Bank": {"lat": 32.0000, "lng": 35.2500},
        "Palestine": {"lat": 31.9522, "lng": 35.2332},
        "Middle East": {"lat": 29.2985, "lng": 42.5510},
    }
    
    known_countries = set(FR_EN_DICT.values()) - {"Paris", "Moscow", "Kyiv", "London", "Beijing", "Rome", "Berlin", "Madrid", "Tokyo"}
    
    results = []
    for city in locations_to_find[:8]:
        if city in geo_cache:
            results.append(geo_cache[city])
            continue
            
        if city in hardcoded_coords:
            data = {
                "name": city,
                "lat": hardcoded_coords[city]["lat"],
                "lng": hardcoded_coords[city]["lng"]
            }
            geo_cache[city] = data
            results.append(data)
            continue
            
        try:
            # If we know it's a country, use a structured query to prevent Nominatim from returning US cities
            query = {"country": city} if city in known_countries else city
            location = geolocator.geocode(query, language="fr", timeout=3)
            
            # Fallback if structured query fails
            if not location and isinstance(query, dict):
                location = geolocator.geocode(city, language="fr", timeout=3)
                
            if location:
                data = {
                    "name": city,
                    "lat": location.latitude,
                    "lng": location.longitude
                }
                geo_cache[city] = data
                results.append(data)
            time.sleep(1.1)
        except Exception:
            obj_class_router["utils"]().error_with_reason("Error with geolocator during exctract location!")
            pass
            
    return {"status": "success", "locations": results}

@app.get("/api/rss")
async def get_rss_feed(url: str):
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Only HTTP/HTTPS URLs are allowed.")
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            return {"status": "error", "message": "Invalid RSS feed."}

        entries = []
        for entry in feed.entries[:15]:
            media_url = ""
            if "media_content" in entry and len(entry.media_content) > 0:
                media_url = entry.media_content[0].get("url", "")
            elif "enclosures" in entry and len(entry.enclosures) > 0:
                for enc in entry.enclosures:
                    if enc.get("type", "").startswith("image/") or enc.get("type", "").startswith("video/"):
                        media_url = enc.get("href", "")
                        break
            
            entries.append({
                "title": entry.get("title", "No Title"),
                "link": entry.get("link", "#"),
                "published": entry.get("published", ""),
                "summary": (entry.get("summary", "")[:200] + "...") if entry.get("summary") else "",
                "media": media_url
            })

        return {
            "title": feed.feed.get("title", "RSS Feed"),
            "entries": entries
        }
    except Exception as e:
        obj_class_router["utils"]().error_with_reason("Error durint get rss feed!")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/rss/upload")
async def upload_rss_feed(file: UploadFile = File(...)):
    try:
        content = await file.read()
        feed = feedparser.parse(content)
        if feed.bozo and not feed.entries:
            return {"status": "error", "message": "Invalid RSS feed."}

        entries = [
            {
                "title": entry.get("title", "No Title"),
                "link": entry.get("link", "#"),
                "published": entry.get("published", ""),
                "summary": (entry.get("summary", "")[:200] + "...") if entry.get("summary") else ""
            }
            for entry in feed.entries[:15]
        ]

        return {
            "title": feed.feed.get("title", "Local RSS File"),
            "entries": entries
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class RssSummarizeRequest(BaseModel):
    entries: list
    api_key: str | None = None
    model: str | None = None
    language: str | None = None

@app.post("/api/rss/summarize")
async def summarize_rss(req: RssSummarizeRequest):
    api_key = req.api_key or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="OpenRouter API Key not found. Please add it to your .env file or Settings.")

    ai_model = req.model or os.getenv("OPENROUTER_MODEL") or "openrouter/free"

    sys_prompt = None
    sys_prompt_b64 = os.getenv("OPENROUTER_SYSTEM_PROMPT")
    if sys_prompt_b64:
        try:
            sys_prompt = base64.b64decode(sys_prompt_b64).decode('utf-8')
        except:
            pass

    if sys_prompt:
        prompt = sys_prompt + "\\n\\nHere are the RSS feed entries:\\n\\n"
    elif req.language == "fr":
        prompt = "Vous êtes un analyste en renseignement professionnel et objectif. Veuillez fournir une synthèse exécutive des entrées de flux RSS suivantes du jour. Regroupez les sujets similaires, mettez en évidence les événements critiques ou les menaces, et maintenez un ton formel et analytique. Utilisez des émojis pertinents uniquement pour les titres majeurs afin de faciliter la lecture. Formatez votre réponse en Markdown propre et structuré :\\n\\n"
    else:
        prompt = "You are a professional, objective intelligence analyst. Please provide an executive summary of the following RSS feed entries from today. Group similar topics, highlight critical events or threats, and maintain a formal, analytical tone. Use relevant emojis only for major section titles to improve readability. Format your response in clean, structured Markdown:\\n\\n"
        
    for idx, entry in enumerate(req.entries):
        time_str = f" [{entry.get('time')}]" if entry.get('time') else ""
        prompt += f"{idx+1}. {entry.get('title')}{time_str} - {entry.get('summary')}\\n"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "KNWLDGBox",
        "Content-Type": "application/json"
    }
    payload = {
        "model": ai_model,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=90.0)
            
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=f"OpenRouter API error: {res.text}")
            
        data = res.json()
        if "choices" not in data or not data["choices"]:
            raise HTTPException(status_code=500, detail=f"Unexpected OpenRouter response: {data}")

        return {"status": "success", "summary": data["choices"][0]["message"]["content"]}
    except HTTPException:
        raise
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="AI generation timed out. The selected model is too slow or overloaded. Please try another model.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    messages: list
    api_key: str | None = None
    model: str | None = None

@app.post("/api/chat")
async def chat_completion(req: ChatRequest):
    api_key = req.api_key or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="OpenRouter API Key not found. Please add it to your Settings.")

    ai_model = req.model or os.getenv("OPENROUTER_MODEL") or "openrouter/free"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "KNWLDGBox",
        "Content-Type": "application/json"
    }
    
    
    sys_prompt_b64 = os.getenv("OPENROUTER_SYSTEM_PROMPT")
    if sys_prompt_b64:
        try:
            sys_prompt = base64.b64decode(sys_prompt_b64).decode('utf-8')
            if req.messages and req.messages[0].get("role") != "system":
                req.messages.insert(0, {"role": "system", "content": sys_prompt})
        except:
            pass

    payload = {
        "model": ai_model,
        "messages": req.messages
    }
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=120.0)
            
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=f"OpenRouter API error: {res.text}")
            
        data = res.json()
        if "choices" not in data or not data["choices"]:
            raise HTTPException(status_code=500, detail=f"Unexpected OpenRouter response: {data}")

        return {"status": "success", "message": data["choices"][0]["message"]}
    except HTTPException:
        raise
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="AI generation timed out.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/telegram/media/{channel}/{message_id}")
async def get_telegram_media(channel: str, message_id: int):
    if not telegram_service.client or not telegram_service.client.is_connected():
        raise HTTPException(status_code=400, detail="Telegram client not connected")
    
    try:
        msg = await telegram_service.client.get_messages(channel, ids=message_id)
        if not msg or not getattr(msg, "media", None):
            raise HTTPException(status_code=404, detail="Media not found")
            
        buffer = await telegram_service.client.download_media(msg, file=bytes)
        if not buffer:
            raise HTTPException(status_code=500, detail="Failed to download media")
            
        mime_type = "application/octet-stream"
        if hasattr(msg, 'file') and msg.file and getattr(msg.file, 'mime_type', None):
            mime_type = msg.file.mime_type
            
        return Response(content=buffer, media_type=mime_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/telegram")
async def websocket_endpoint(websocket: WebSocket):
    await telegram_service.handle_websocket(websocket)

@app.websocket("/ws/sherlock")
async def sherlock_endpoint(websocket: WebSocket):
    await sherlock_service.handle_websocket(websocket)


# Must be the LAST mount so /api/* and /ws/* routes take priority.
# In dev mode, app/dist won't exist and this block is skipped entirely.
from config import APP_DIR
from starlette.exceptions import HTTPException as StarletteHTTPException

class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (HTTPException, StarletteHTTPException) as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            raise

_frontend_dist = APP_DIR.parent / "app" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", SPAStaticFiles(directory=str(_frontend_dist), html=True), name="frontend")

