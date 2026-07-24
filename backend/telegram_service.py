import asyncio
import os
from typing import Any

import routerClass
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from fastapi import WebSocket

class TelegramService:
    def __init__(self):
        self.client: TelegramClient | None = None
        self.active_connections: list[dict[str, Any]] = []
        self.last_message_ids: dict[str, int] = {}
        self.phone_code_hash: str | None = None
        self.monitoring_task: asyncio.Task | None = None
        self._is_polling = False
        self.obj_class_router = routerClass.routerFunctionPipe("backend")
    def get_credentials(self):
        return os.getenv('TG_API_ID'), os.getenv('TG_API_HASH'), os.getenv('TG_PHONE')

    async def initialize(self) -> dict:
        api_id, api_hash, phone = self.get_credentials()
        
        if not api_id or not api_hash:
            return {"status": "error", "message": "API credentials missing."}

        if self.client:
            await self.client.disconnect()

        try:
            from config import SESSION_NAME
            self.client = TelegramClient(SESSION_NAME, int(api_id), api_hash)
        except:
            self.obj_class_router["utils"]().error_with_reason("Please configure your Telegram api key!")

        try:
            await self.client.connect()
            if not await self.client.is_user_authorized():
                return {"status": "needs_auth"}
                
            self.start_polling()
            return {"status": "authorized"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def disconnect(self):
        self._is_polling = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
        if self.client:
            await self.client.disconnect()

    async def send_auth_code(self) -> dict:
        _, _, phone = self.get_credentials()
        if not self.client or not self.client.is_connected():
            await self.initialize()
            
        result = await self.client.send_code_request(phone)
        self.phone_code_hash = result.phone_code_hash
        return {"status": "success", "message": "Code sent"}

    async def verify_auth_code(self, code: str) -> dict:
        _, _, phone = self.get_credentials()
        try:
            await self.client.sign_in(phone, code, phone_code_hash=self.phone_code_hash)
            self.start_polling()
            return {"status": "success"}
        except SessionPasswordNeededError:
            raise ValueError("2FA is enabled. Please disable it temporarily.")
        except Exception as e:
            raise ValueError(str(e))

    def start_polling(self):
        if not self._is_polling:
            self._is_polling = True
            self.monitoring_task = asyncio.create_task(self._poll_channels())

    async def _poll_channels(self):
        while self._is_polling:
            if not self.client or not self.client.is_connected() or not await self.client.is_user_authorized():
                await asyncio.sleep(5)
                continue
                
            all_channels = {ch for conn in self.active_connections for ch in conn["channels"]}
                
            for channel in all_channels:
                try:
                    messages = await self.client.get_messages(channel, limit=1)
                    if not messages:
                        continue
                        
                    msg = messages[0]
                    state_key = channel
                    
                    if state_key not in self.last_message_ids or self.last_message_ids[state_key] < msg.id:
                        self.last_message_ids[state_key] = msg.id
                        
                        message_data = {
                            "channel": channel,
                            "id": msg.id,
                            "text": msg.raw_text or "[Media/No Text]",
                            "time": msg.date.strftime("%Y-%m-%d %H:%M:%S") if msg.date else "",
                            "author": channel,
                            "has_media": msg.media is not None,
                            "media_type": "video" if getattr(msg, 'video', None) else "photo"
                        }
                        
                        await self.broadcast(channel, message_data)
                except Exception:
                    pass # Ignore errors for single channels to prevent loop crash
                    
            await asyncio.sleep(4)

    async def broadcast(self, channel: str, message_data: dict):
        for conn in self.active_connections:
            if channel in conn["channels"]:
                try:
                    await conn["ws"].send_json(message_data)
                except Exception:
                    pass

    async def handle_websocket(self, websocket: WebSocket):
        await websocket.accept()
        connection = {"ws": websocket, "channels": set()}
        self.active_connections.append(connection)
        
        try:
            while True:
                payload = await websocket.receive_json()
                action = payload.get("action")
                channel = payload.get("channel", "").lower().replace("@", "")
                
                if action == "subscribe" and channel:
                    await self._subscribe_ws(connection, channel, websocket)
                elif action == "unsubscribe" and channel:
                    if channel in connection["channels"]:
                        connection["channels"].remove(channel)
        except Exception:
            pass
        finally:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

    async def _subscribe_ws(self, connection: dict, channel: str, websocket: WebSocket):
        if self.client and self.client.is_connected():
            if not await self.client.is_user_authorized():
                await websocket.send_json({
                    "channel": channel, "id": 0, 
                    "text": "[Error] Not authorized. Configure Telegram in Settings.", 
                    "time": "", "author": "System"
                })
            else:
                try:
                    await self.client.get_entity(channel)
                    await websocket.send_json({
                        "channel": channel, "id": 0, 
                        "text": f"[Connected] Polling for messages from @{channel}...", 
                        "time": "", "author": "System"
                    })
                    
                    try:
                        history = await self.client.get_messages(channel, limit=10)
                        for msg in reversed(history):
                            if msg.id:
                                await websocket.send_json({
                                    "channel": channel,
                                    "id": msg.id,
                                    "text": msg.raw_text or "[Media/No Text]",
                                    "time": msg.date.strftime("%Y-%m-%d %H:%M:%S") if msg.date else "",
                                    "author": channel,
                                    "has_media": msg.media is not None,
                                    "media_type": "video" if getattr(msg, 'video', None) else "photo"
                                })
                        if history:
                            self.last_message_ids[channel] = max(self.last_message_ids.get(channel, 0), history[0].id)
                    except Exception:
                        pass

                    connection["channels"].add(channel)
                except Exception:
                    await websocket.send_json({
                        "channel": channel, "id": 0, 
                        "text": f"[Error] Could not find @{channel}.", 
                        "time": "", "author": "System"
                    })

telegram_service = TelegramService()
