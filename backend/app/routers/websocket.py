import json
import asyncio
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """WebSocket connection manager for real-time notifications."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._subscriptions: Dict[str, Set[str]] = {}  # file_id -> set of client_ids

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"[WS] Client connected: {client_id}")

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
        # Clean up subscriptions
        for file_id in list(self._subscriptions.keys()):
            self._subscriptions[file_id].discard(client_id)
            if not self._subscriptions[file_id]:
                del self._subscriptions[file_id]
        print(f"[WS] Client disconnected: {client_id}")

    def subscribe(self, client_id: str, file_id: str):
        if file_id not in self._subscriptions:
            self._subscriptions[file_id] = set()
        self._subscriptions[file_id].add(client_id)

    async def send_personal_message(self, message: dict, client_id: str):
        websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(client_id)

    async def broadcast(self, message: dict):
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(client_id)
        for client_id in disconnected:
            self.disconnect(client_id)

    async def notify_file_subscribers(self, file_id: str, message: dict):
        """Send a message to all clients subscribed to a specific file_id."""
        subscribers = self._subscriptions.get(file_id, set())
        disconnected = []
        for client_id in subscribers:
            websocket = self.active_connections.get(client_id)
            if websocket:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(client_id)
        for client_id in disconnected:
            self.disconnect(client_id)


# Singleton instance
manager = ConnectionManager()


def get_manager() -> ConnectionManager:
    return manager


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "subscribe":
                file_id = msg.get("file_id")
                if file_id:
                    manager.subscribe(client_id, file_id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "file_id": file_id
                    })

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"[WS] Error for client {client_id}: {e}")
        manager.disconnect(client_id)
