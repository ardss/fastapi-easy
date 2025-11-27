# WebSocket 支持

fastapi-easy 支持 WebSocket 实时通信。本指南介绍如何使用 WebSocket 功能。

---

## 启用 WebSocket

```python
from fastapi_easy.websocket import WebSocketConfig

config = WebSocketConfig(
    enabled=True,
    endpoint="/ws",
    max_connections=1000,
)
```

---

## WebSocket 连接

```python
from fastapi_easy.websocket import get_connection_manager

manager = get_connection_manager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data)
    finally:
        await manager.disconnect(client_id)
```

---

## 房间管理

```python
from fastapi_easy.websocket import get_room_manager

room_manager = get_room_manager()

# 添加客户端到房间
room_manager.add_client_to_room("room1", "client1")

# 获取房间中的客户端
clients = room_manager.get_room_clients("room1")
```

---

**下一步**: [CLI 工具](17-cli-tools.md) →
