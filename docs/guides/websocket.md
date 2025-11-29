# WebSocket 支持

FastAPI-Easy 支持 WebSocket 实时通信。本文档介绍如何使用 WebSocket。

---

## 启用 WebSocket

```python
from fastapi import WebSocket
from fastapi_easy import CRUDRouter

@app.websocket("/ws/items")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except Exception as e:
        await websocket.close()
```

---

## WebSocket 连接

### 客户端连接

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/items");

ws.onopen = function(event) {
    console.log("Connected");
    ws.send("Hello");
};

ws.onmessage = function(event) {
    console.log("Message:", event.data);
};

ws.onclose = function(event) {
    console.log("Disconnected");
};
```

---

## 实时数据推送

### 服务器端

```python
@app.websocket("/ws/items")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 从数据库获取最新数据
            items = db.query(Item).all()
            await websocket.send_json([item.dict() for item in items])
            await asyncio.sleep(1)
    except Exception as e:
        await websocket.close()
```

### 客户端

```javascript
ws.onmessage = function(event) {
    const items = JSON.parse(event.data);
    console.log("Items:", items);
};
```

---

## 最佳实践

### 1. 错误处理

```python
@app.websocket("/ws/items")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()
```

### 2. 连接管理

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)
```

---

## 常见问题

### Q: 如何处理 WebSocket 断开连接？
A: 使用 try-except 捕获 WebSocketDisconnect 异常。

### Q: 如何广播消息给所有连接？
A: 使用 ConnectionManager 管理所有连接。

### Q: 如何在 WebSocket 中发送 JSON 数据？
A: 使用 `websocket.send_json()` 方法。
