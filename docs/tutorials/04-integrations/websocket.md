# WebSocket 集成

**难度**: ⭐⭐⭐ 中级  
**预计时间**: 15 分钟  
**前置知识**: [快速开始](../01-basics/quick-start.md)

---

## 概述

FastAPI-Easy 支持 WebSocket 集成，允许实时推送数据更新。WebSocket 提供了双向通信能力，非常适合需要实时更新的应用场景。

### 适用场景

- 📊 实时数据仪表板
- 💬 聊天应用
- 🔔 实时通知系统
- 📈 实时数据监控
- 🎮 多人协作应用

---

## 快速开始

### 基础配置

```python
from fastapi import FastAPI, WebSocket
from fastapi_easy import CRUDRouter
from fastapi_easy.websocket import setup_websocket
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    price: float

app = FastAPI()

# 创建 CRUD 路由
router = CRUDRouter(schema=Item)
app.include_router(router)

# 启用 WebSocket
setup_websocket(app, [Item])
```

### 简单的 WebSocket 端点

```python
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

## 客户端连接

### JavaScript 客户端

```javascript
// 连接到 WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/items');

ws.onopen = (event) => {
    console.log('Connected');
    ws.send('Hello Server!');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onerror = (error) => {
    console.error('Error:', error);
};

ws.onclose = (event) => {
    console.log('Disconnected');
};
```

### Python 客户端

```python
import asyncio
import websockets

async def connect():
    uri = "ws://localhost:8000/ws/items"
    async with websockets.connect(uri) as websocket:
        await websocket.send("Hello Server!")
        response = await websocket.recv()
        print(f"Received: {response}")

asyncio.run(connect())
```

---

## 消息格式

### 创建事件

```json
{
  "type": "create",
  "resource": "items",
  "data": {
    "id": 1,
    "name": "apple",
    "price": 10.5
  }
}
```

### 更新事件

```json
{
  "type": "update",
  "resource": "items",
  "id": 1,
  "data": {
    "name": "orange",
    "price": 12.0
  }
}
```

### 删除事件

```json
{
  "type": "delete",
  "resource": "items",
  "id": 1
}
```

---

## 实时更新示例

### 订阅项目更新

```python
from fastapi import WebSocket

@app.websocket("/ws/items")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            
            # 处理订阅请求
            if data.get("type") == "subscribe":
                # 发送初始数据
                items = await get_all_items()
                await websocket.send_json({
                    "type": "initial",
                    "data": items
                })
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()
```

### 实时数据推送

```python
@app.websocket("/ws/items")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 从数据库获取最新数据
            items = await db.query(Item).all()
            await websocket.send_json([item.dict() for item in items])
            await asyncio.sleep(1)  # 每秒推送一次
    except Exception as e:
        await websocket.close()
```

### 广播更新

```python
# 当项目被创建时，广播给所有连接的客户端
async def on_item_created(item):
    for connection in active_connections:
        await connection.send_json({
            "type": "create",
            "resource": "items",
            "data": item.dict()
        })
```

---

## 连接管理

### ConnectionManager 类

```python
from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

# 创建全局连接管理器
manager = ConnectionManager()
```

### 使用 ConnectionManager

```python
@app.websocket("/ws/items")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 广播给所有连接
            await manager.broadcast(f"Client says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("A client disconnected")
```

---

## 错误处理

### 连接错误

```python
from fastapi import WebSocketDisconnect

@app.websocket("/ws/items")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return
    
    try:
        while True:
            data = await websocket.receive_json()
            # 处理数据
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error: {e}")
        await websocket.close(code=1000)
```

### 超时处理

```python
import asyncio

@app.websocket("/ws/items")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 设置 30 秒超时
            data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=30.0
            )
            await websocket.send_json({"echo": data})
    except asyncio.TimeoutError:
        logger.warning("Connection timeout")
        await websocket.close(code=1000)
```

---

## 高级功能

### 1. 心跳检测

```python
async def heartbeat(websocket: WebSocket):
    while True:
        try:
            await websocket.send_json({"type": "ping"})
            await asyncio.sleep(30)  # 每 30 秒发送一次心跳
        except:
            break

@app.websocket("/ws/items")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # 启动心跳任务
    heartbeat_task = asyncio.create_task(heartbeat(websocket))
    
    try:
        while True:
            data = await websocket.receive_json()
            # 处理数据
    finally:
        heartbeat_task.cancel()
        await websocket.close()
```

### 2. 消息队列

```python
from asyncio import Queue

message_queue = Queue()

async def message_processor():
    while True:
        message = await message_queue.get()
        # 处理消息
        await manager.broadcast(message)

@app.on_event("startup")
async def startup():
    asyncio.create_task(message_processor())
```

### 3. 认证和授权

```python
from fastapi import WebSocket, HTTPException, status

async def verify_token(token: str) -> bool:
    # 验证 token
    return True

@app.websocket("/ws/items")
async def websocket_endpoint(websocket: WebSocket, token: str):
    if not await verify_token(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    await websocket.accept()
    # 继续处理...
```

---

## 最佳实践

1. **心跳检测** - 定期发送心跳保持连接活跃
2. **消息队列** - 使用队列管理消息，避免阻塞
3. **连接管理** - 使用 ConnectionManager 跟踪活跃连接
4. **错误恢复** - 客户端实现自动重连机制
5. **性能监控** - 监控连接数和消息吞吐量
6. **认证授权** - 验证 WebSocket 连接的身份
7. **消息限流** - 防止消息洪水攻击
8. **优雅关闭** - 正确处理连接关闭

---

## 常见问题

**Q: 如何处理 WebSocket 断开连接？**

A: 使用 try-except 捕获 `WebSocketDisconnect` 异常：
```python
try:
    while True:
        data = await websocket.receive_json()
except WebSocketDisconnect:
    logger.info("Client disconnected")
```

**Q: 如何广播消息给所有连接？**

A: 使用 ConnectionManager 管理所有连接并实现广播方法。

**Q: 如何在 WebSocket 中发送 JSON 数据？**

A: 使用 `websocket.send_json()` 方法：
```python
await websocket.send_json({"message": "Hello"})
```

**Q: WebSocket 连接数量有限制吗？**

A: 理论上没有限制，但实际受服务器资源限制。建议监控连接数并设置合理上限。

---

## 性能优化

1. **使用消息批处理** - 批量发送消息减少网络开销
2. **压缩消息** - 对大消息使用压缩
3. **连接池** - 复用连接减少开销
4. **异步处理** - 使用异步任务处理耗时操作

---

## 总结

WebSocket 集成提供了强大的实时通信能力，适合需要实时更新的应用。通过合理的连接管理、错误处理和性能优化，可以构建稳定高效的实时应用。

---

**下一步**: [数据库迁移](migrations.md) →
