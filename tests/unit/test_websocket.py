"""Unit tests for WebSocket support"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi_easy.websocket import (
    WebSocketMessage,
    WebSocketConnectionManager,
    WebSocketRoom,
    WebSocketRoomManager,
    WebSocketConfig,
    get_connection_manager,
    get_room_manager,
)


class TestWebSocketMessage:
    """Test WebSocketMessage"""

    def test_message_initialization(self):
        """Test message initialization"""
        msg = WebSocketMessage("test", {"key": "value"}, client_id="client1")

        assert msg.type == "test"
        assert msg.data == {"key": "value"}
        assert msg.client_id == "client1"
        assert msg.timestamp is not None

    def test_message_to_dict(self):
        """Test converting message to dict"""
        msg = WebSocketMessage("test", {"key": "value"}, client_id="client1")

        msg_dict = msg.to_dict()

        assert msg_dict["type"] == "test"
        assert msg_dict["data"] == {"key": "value"}
        assert msg_dict["client_id"] == "client1"

    def test_message_to_json(self):
        """Test converting message to JSON"""
        msg = WebSocketMessage("test", {"key": "value"})

        msg_json = msg.to_json()

        assert "test" in msg_json
        assert "key" in msg_json


class TestWebSocketConnectionManager:
    """Test WebSocketConnectionManager"""

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test connecting client"""
        manager = WebSocketConnectionManager()
        ws = AsyncMock()

        await manager.connect("client1", ws)

        assert "client1" in manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnecting client"""
        manager = WebSocketConnectionManager()
        ws = AsyncMock()

        await manager.connect("client1", ws)
        await manager.disconnect("client1")

        assert "client1" not in manager.active_connections

    @pytest.mark.asyncio
    async def test_send_personal(self):
        """Test sending personal message"""
        manager = WebSocketConnectionManager()
        ws = AsyncMock()

        await manager.connect("client1", ws)
        msg = WebSocketMessage("test", {"data": "value"})

        await manager.send_personal("client1", msg)

        ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_personal_nonexistent(self):
        """Test sending to nonexistent client"""
        manager = WebSocketConnectionManager()
        msg = WebSocketMessage("test", {"data": "value"})

        # Should not raise error
        await manager.send_personal("nonexistent", msg)

    @pytest.mark.asyncio
    async def test_broadcast(self):
        """Test broadcasting message"""
        manager = WebSocketConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await manager.connect("client1", ws1)
        await manager.connect("client2", ws2)

        msg = WebSocketMessage("test", {"data": "value"})
        await manager.broadcast(msg)

        assert ws1.send_json.call_count == 1
        assert ws2.send_json.call_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_exclude(self):
        """Test broadcasting with exclusion"""
        manager = WebSocketConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await manager.connect("client1", ws1)
        await manager.connect("client2", ws2)

        msg = WebSocketMessage("test", {"data": "value"})
        await manager.broadcast(msg, exclude_client="client1")

        assert ws1.send_json.call_count == 0
        assert ws2.send_json.call_count == 1

    @pytest.mark.asyncio
    async def test_register_handler(self):
        """Test registering message handler"""
        manager = WebSocketConnectionManager()

        async def handler(msg):
            return msg.data

        manager.register_handler("test", handler)

        assert "test" in manager.message_handlers

    @pytest.mark.asyncio
    async def test_handle_message_async(self):
        """Test handling async message"""
        manager = WebSocketConnectionManager()

        async def handler(msg):
            return {"result": "success"}

        manager.register_handler("test", handler)
        msg = WebSocketMessage("test", {"data": "value"})

        result = await manager.handle_message(msg)

        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_handle_message_sync(self):
        """Test handling sync message"""
        manager = WebSocketConnectionManager()

        def handler(msg):
            return {"result": "success"}

        manager.register_handler("test", handler)
        msg = WebSocketMessage("test", {"data": "value"})

        result = await manager.handle_message(msg)

        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_handle_message_no_handler(self):
        """Test handling message without handler"""
        manager = WebSocketConnectionManager()
        msg = WebSocketMessage("unknown", {"data": "value"})

        result = await manager.handle_message(msg)

        assert result is None

    def test_get_connected_clients(self):
        """Test getting connected clients"""
        manager = WebSocketConnectionManager()
        manager.active_connections["client1"] = AsyncMock()
        manager.active_connections["client2"] = AsyncMock()

        clients = manager.get_connected_clients()

        assert len(clients) == 2
        assert "client1" in clients
        assert "client2" in clients

    def test_get_client_count(self):
        """Test getting client count"""
        manager = WebSocketConnectionManager()
        manager.active_connections["client1"] = AsyncMock()
        manager.active_connections["client2"] = AsyncMock()

        count = manager.get_client_count()

        assert count == 2


class TestWebSocketRoom:
    """Test WebSocketRoom"""

    def test_room_initialization(self):
        """Test room initialization"""
        room = WebSocketRoom("room1")

        assert room.room_id == "room1"
        assert room.clients == set()

    def test_add_client(self):
        """Test adding client to room"""
        room = WebSocketRoom("room1")

        room.add_client("client1")

        assert "client1" in room.clients

    def test_remove_client(self):
        """Test removing client from room"""
        room = WebSocketRoom("room1")
        room.add_client("client1")

        room.remove_client("client1")

        assert "client1" not in room.clients

    def test_has_client(self):
        """Test checking if client is in room"""
        room = WebSocketRoom("room1")
        room.add_client("client1")

        assert room.has_client("client1") is True
        assert room.has_client("client2") is False

    def test_get_clients(self):
        """Test getting clients in room"""
        room = WebSocketRoom("room1")
        room.add_client("client1")
        room.add_client("client2")

        clients = room.get_clients()

        assert len(clients) == 2
        assert "client1" in clients
        assert "client2" in clients

    def test_get_client_count(self):
        """Test getting client count in room"""
        room = WebSocketRoom("room1")
        room.add_client("client1")
        room.add_client("client2")

        count = room.get_client_count()

        assert count == 2


class TestWebSocketRoomManager:
    """Test WebSocketRoomManager"""

    def test_create_room(self):
        """Test creating room"""
        manager = WebSocketRoomManager()

        room = manager.create_room("room1")

        assert room is not None
        assert room.room_id == "room1"

    def test_get_room(self):
        """Test getting room"""
        manager = WebSocketRoomManager()
        manager.create_room("room1")

        room = manager.get_room("room1")

        assert room is not None
        assert room.room_id == "room1"

    def test_get_nonexistent_room(self):
        """Test getting nonexistent room"""
        manager = WebSocketRoomManager()

        room = manager.get_room("nonexistent")

        assert room is None

    def test_delete_room(self):
        """Test deleting room"""
        manager = WebSocketRoomManager()
        manager.create_room("room1")

        manager.delete_room("room1")

        assert manager.get_room("room1") is None

    def test_add_client_to_room(self):
        """Test adding client to room"""
        manager = WebSocketRoomManager()

        manager.add_client_to_room("room1", "client1")

        room = manager.get_room("room1")
        assert room.has_client("client1")

    def test_remove_client_from_room(self):
        """Test removing client from room"""
        manager = WebSocketRoomManager()
        manager.add_client_to_room("room1", "client1")

        manager.remove_client_from_room("room1", "client1")

        # Room should be deleted if empty
        assert manager.get_room("room1") is None

    def test_get_room_clients(self):
        """Test getting clients in room"""
        manager = WebSocketRoomManager()
        manager.add_client_to_room("room1", "client1")
        manager.add_client_to_room("room1", "client2")

        clients = manager.get_room_clients("room1")

        assert len(clients) == 2

    def test_get_rooms(self):
        """Test getting list of rooms"""
        manager = WebSocketRoomManager()
        manager.create_room("room1")
        manager.create_room("room2")

        rooms = manager.get_rooms()

        assert len(rooms) == 2
        assert "room1" in rooms
        assert "room2" in rooms


class TestWebSocketConfig:
    """Test WebSocketConfig"""

    def test_default_config(self):
        """Test default configuration"""
        config = WebSocketConfig()

        assert config.enabled is True
        assert config.endpoint == "/ws"
        assert config.max_connections == 1000
        assert config.message_queue_size == 100

    def test_custom_config(self):
        """Test custom configuration"""
        config = WebSocketConfig(
            enabled=False,
            endpoint="/api/ws",
            max_connections=500,
            message_queue_size=50,
        )

        assert config.enabled is False
        assert config.endpoint == "/api/ws"
        assert config.max_connections == 500
        assert config.message_queue_size == 50


class TestGlobalInstances:
    """Test global instances"""

    def test_get_connection_manager(self):
        """Test getting connection manager"""
        manager = get_connection_manager()

        assert manager is not None
        assert isinstance(manager, WebSocketConnectionManager)

    def test_connection_manager_singleton(self):
        """Test connection manager is singleton"""
        manager1 = get_connection_manager()
        manager2 = get_connection_manager()

        assert manager1 is manager2

    def test_get_room_manager(self):
        """Test getting room manager"""
        manager = get_room_manager()

        assert manager is not None
        assert isinstance(manager, WebSocketRoomManager)

    def test_room_manager_singleton(self):
        """Test room manager is singleton"""
        manager1 = get_room_manager()
        manager2 = get_room_manager()

        assert manager1 is manager2
