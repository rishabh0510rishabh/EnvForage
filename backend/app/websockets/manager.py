
# --- Real-Time WebSockets Architecture ---
import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("WebSocketManager")

class ConnectionManager:
    """
    Advanced WebSocket Manager supporting pub/sub-like topics,
    connection lifecycle management, and targeted broadcasting.
    """
    def __init__(self):
        # Maps client_id to WebSocket
        self.active_connections: dict[str, WebSocket] = {}
        # Maps topic to list of client_ids
        self.topics: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket
        logger.info(f"WebSocket Client connected: {client_id}")

    async def disconnect(self, client_id: str):
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            for topic, clients in self.topics.items():
                if client_id in clients:
                    clients.remove(client_id)
        logger.info(f"WebSocket Client disconnected: {client_id}")

    async def subscribe(self, client_id: str, topic: str):
        async with self._lock:
            if topic not in self.topics:
                self.topics[topic] = []
            if client_id not in self.topics[topic]:
                self.topics[topic].append(client_id)
        logger.debug(f"Client {client_id} subscribed to {topic}")

    async def unsubscribe(self, client_id: str, topic: str):
        async with self._lock:
            if topic in self.topics and client_id in self.topics[topic]:
                self.topics[topic].remove(client_id)

    async def send_personal_message(self, message: Any, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")
                await self.disconnect(client_id)

    async def broadcast_to_topic(self, topic: str, message: Any):
        if topic in self.topics:
            clients = self.topics[topic].copy()
            tasks = [self.send_personal_message(message, client_id) for client_id in clients]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def ping_clients(self):
        """Background task to ping clients and cleanup dead connections."""
        while True:
            await asyncio.sleep(30)
            async with self._lock:
                clients = list(self.active_connections.keys())
            for client_id in clients:
                await self.send_personal_message({"type": "ping"}, client_id)

websocket_manager = ConnectionManager()
