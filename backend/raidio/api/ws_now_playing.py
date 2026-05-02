import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class NowPlayingManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict[str, Any]) -> None:
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                pass


now_playing_manager = NowPlayingManager()


@router.websocket("/ws/now-playing")
async def now_playing_websocket(websocket: WebSocket):
    await now_playing_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                await websocket.send_json({"received": msg})
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
    except WebSocketDisconnect:
        now_playing_manager.disconnect(websocket)
    except Exception:
        now_playing_manager.disconnect(websocket)


def get_now_playing_manager() -> NowPlayingManager:
    return now_playing_manager

