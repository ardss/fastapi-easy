# WebSocket 集成指南

**难度**: ⭐⭐⭐ 中级  
**预计时间**: 15 分钟  
**前置知识**: [快速开始](../tutorial/01-quick-start.md)

---

## 概述

FastAPI-Easy 支持 WebSocket 集成，允许实时推送数据更新。

---

## 启用 WebSocket

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

---

## WebSocket 连接

### 连接到 WebSocket

```javascript
// JavaScript 客户端
const ws = new WebSocket('ws://localhost:8000/ws/items');

ws.onopen = (event) => {
    console.log('Connected');
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

## 错误处理

### 连接错误

```python
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

---

## 最佳实践

1. **心跳检测** - 定期发送心跳保持连接
2. **消息队列** - 使用队列管理消息
3. **连接管理** - 跟踪活跃连接
4. **错误恢复** - 实现重连机制
5. **性能监控** - 监控连接数和消息吞吐量

---

## 总结

WebSocket 集成提供了实时通信能力，适合需要实时更新的应用。

