"""WebSocket support for FastAPI-Easy"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set


class WebSocketMessage:
    """WebSocket message"""

    def __init__(
        self,
        type: str,
        data: Any,
        client_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ):
        """Initialize WebSocket message

        Args:
            type: Message type
            data: Message data
            client_id: Client ID
            timestamp: Message timestamp
        """
        self.type = type
        self.data = data
        self.client_id = client_id
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary

        Returns:
            Message as dictionary
        """
        return {
            "type": self.type,
            "data": self.data,
            "client_id": self.client_id,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        """Convert to JSON

        Returns:
            Message as JSON string
        """
        return json.dumps(self.to_dict())


class WebSocketConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        """Initialize connection manager"""
        self.active_connections: Dict[str, Any] = {}
        self.message_handlers: Dict[str, Callable] = {}

    async def connect(self, client_id: str, websocket: Any) -> None:
        """Connect a client

        Args:
            client_id: Client ID
            websocket: WebSocket connection
        """
        self.active_connections[client_id] = websocket

    async def disconnect(self, client_id: str) -> None:
        """Disconnect a client

        Args:
            client_id: Client ID
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal(self, client_id: str, message: WebSocketMessage) -> None:
        """Send message to specific client

        Args:
            client_id: Client ID
            message: Message to send
        """
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_json(message.to_dict())

    async def broadcast(
        self, message: WebSocketMessage, exclude_client: Optional[str] = None
    ) -> None:
        """Broadcast message to all clients

        Args:
            message: Message to send
            exclude_client: Client ID to exclude
        """
        for client_id, websocket in self.active_connections.items():
            if exclude_client and client_id == exclude_client:
                continue

            try:
                await websocket.send_json(message.to_dict())
            except (RuntimeError, ConnectionError, Exception) as e:
                # Handle disconnected clients gracefully
                # Log the error if logger is available
                logger = getattr(self, "logger", None)
                if logger:
                    logger.debug(f"Failed to send message to {client_id}: {e}")

    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register message handler

        Args:
            message_type: Message type
            handler: Handler function
        """
        self.message_handlers[message_type] = handler

    async def handle_message(self, message: WebSocketMessage) -> Any:
        """Handle incoming message

        Args:
            message: Incoming message

        Returns:
            Handler result
        """
        handler = self.message_handlers.get(message.type)

        if handler:
            if asyncio.iscoroutinefunction(handler):
                return await handler(message)
            else:
                return handler(message)

        return None

    def get_connected_clients(self) -> List[str]:
        """Get list of connected clients

        Returns:
            List of client IDs
        """
        return list(self.active_connections.keys())

    def get_client_count(self) -> int:
        """Get number of connected clients

        Returns:
            Number of clients
        """
        return len(self.active_connections)


class WebSocketRoom:
    """WebSocket room for grouping clients"""

    def __init__(self, room_id: str):
        """Initialize room

        Args:
            room_id: Room ID
        """
        self.room_id = room_id
        self.clients: Set[str] = set()

    def add_client(self, client_id: str) -> None:
        """Add client to room

        Args:
            client_id: Client ID
        """
        self.clients.add(client_id)

    def remove_client(self, client_id: str) -> None:
        """Remove client from room

        Args:
            client_id: Client ID
        """
        self.clients.discard(client_id)

    def has_client(self, client_id: str) -> bool:
        """Check if client is in room

        Args:
            client_id: Client ID

        Returns:
            True if client is in room
        """
        return client_id in self.clients

    def get_clients(self) -> List[str]:
        """Get list of clients in room

        Returns:
            List of client IDs
        """
        return list(self.clients)

    def get_client_count(self) -> int:
        """Get number of clients in room

        Returns:
            Number of clients
        """
        return len(self.clients)


class WebSocketRoomManager:
    """Manages WebSocket rooms"""

    def __init__(self):
        """Initialize room manager"""
        self.rooms: Dict[str, WebSocketRoom] = {}

    def create_room(self, room_id: str) -> WebSocketRoom:
        """Create a room

        Args:
            room_id: Room ID

        Returns:
            Room instance
        """
        if room_id not in self.rooms:
            self.rooms[room_id] = WebSocketRoom(room_id)

        return self.rooms[room_id]

    def get_room(self, room_id: str) -> Optional[WebSocketRoom]:
        """Get a room

        Args:
            room_id: Room ID

        Returns:
            Room instance or None
        """
        return self.rooms.get(room_id)

    def delete_room(self, room_id: str) -> None:
        """Delete a room

        Args:
            room_id: Room ID
        """
        if room_id in self.rooms:
            del self.rooms[room_id]

    def add_client_to_room(self, room_id: str, client_id: str) -> None:
        """Add client to room

        Args:
            room_id: Room ID
            client_id: Client ID
        """
        room = self.create_room(room_id)
        room.add_client(client_id)

    def remove_client_from_room(self, room_id: str, client_id: str) -> None:
        """Remove client from room

        Args:
            room_id: Room ID
            client_id: Client ID
        """
        room = self.get_room(room_id)

        if room:
            room.remove_client(client_id)

            # Delete room if empty
            if room.get_client_count() == 0:
                self.delete_room(room_id)

    def get_room_clients(self, room_id: str) -> List[str]:
        """Get clients in room

        Args:
            room_id: Room ID

        Returns:
            List of client IDs
        """
        room = self.get_room(room_id)

        if room:
            return room.get_clients()

        return []

    def get_rooms(self) -> List[str]:
        """Get list of rooms

        Returns:
            List of room IDs
        """
        return list(self.rooms.keys())


class WebSocketConfig:
    """Configuration for WebSocket"""

    def __init__(
        self,
        enabled: bool = True,
        endpoint: str = "/ws",
        max_connections: int = 1000,
        message_queue_size: int = 100,
    ):
        """Initialize WebSocket configuration

        Args:
            enabled: Enable WebSocket
            endpoint: WebSocket endpoint
            max_connections: Maximum connections
            message_queue_size: Message queue size
        """
        self.enabled = enabled
        self.endpoint = endpoint
        self.max_connections = max_connections
        self.message_queue_size = message_queue_size


# Global instances
_connection_manager: Optional[WebSocketConnectionManager] = None
_room_manager: Optional[WebSocketRoomManager] = None


def get_connection_manager() -> WebSocketConnectionManager:
    """Get global connection manager

    Returns:
        Connection manager instance
    """
    global _connection_manager

    if _connection_manager is None:
        _connection_manager = WebSocketConnectionManager()

    return _connection_manager


def get_room_manager() -> WebSocketRoomManager:
    """Get global room manager

    Returns:
        Room manager instance
    """
    global _room_manager

    if _room_manager is None:
        _room_manager = WebSocketRoomManager()

    return _room_manager
