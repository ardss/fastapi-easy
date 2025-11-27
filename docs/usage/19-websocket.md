# WebSocket 支持

FastAPI-Easy 提供了完整的 WebSocket 支持，用于实时双向通信。

---

## 什么是 WebSocket？

WebSocket 是一种网络协议，提供了在单个 TCP 连接上进行全双工通信的能力。

**优势**:
- ✅ **实时通信** - 低延迟的双向通信
- ✅ **减少开销** - 相比 HTTP 轮询更高效
- ✅ **连接持久** - 保持长连接
- ✅ **事件驱动** - 基于事件的通信模式

---

## 基础使用

### 1. 安装依赖

```bash
pip install fastapi-easy[websocket]
pip install websockets
```

### 2. 创建 WebSocket 消息

```python
from fastapi_easy.websocket import WebSocketMessage

# 创建消息
message = WebSocketMessage(
    type="chat",
    data={"text": "Hello, World!"},
    client_id="client_1"
)

# 转换为字典
msg_dict = message.to_dict()
print(msg_dict)
# 输出：
# {
#   "type": "chat",
#   "data": {"text": "Hello, World!"},
#   "client_id": "client_1",
#   "timestamp": "2024-11-28T10:30:45.123456"
# }

# 转换为 JSON
msg_json = message.to_json()
print(msg_json)
```

### 3. 管理 WebSocket 连接

```python
from fastapi_easy.websocket import WebSocketConnectionManager

# 创建连接管理器
manager = WebSocketConnectionManager()

# 连接客户端
await manager.connect("client_1", websocket)

# 发送个人消息
message = WebSocketMessage(
    type="notification",
    data={"message": "Welcome!"},
    client_id="client_1"
)
await manager.send_personal("client_1", message)

# 广播消息
broadcast_msg = WebSocketMessage(
    type="announcement",
    data={"message": "New user joined"},
)
await manager.broadcast(broadcast_msg, exclude_client="client_1")

# 断开连接
await manager.disconnect("client_1")
```

---

## 完整示例

### 项目结构

```
my_websocket_app/
├── main.py              # FastAPI 应用
├── models.py            # 数据模型
├── requirements.txt     # 依赖
└── static/
    └── index.html       # 前端页面
```

### 1. 创建 FastAPI 应用

**main.py**:
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi_easy.websocket import WebSocketConnectionManager, WebSocketMessage
import json
import uuid

app = FastAPI()

# 创建连接管理器
manager = WebSocketConnectionManager()

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket 端点"""
    await websocket.accept()
    
    # 连接客户端
    await manager.connect(client_id, websocket)
    
    # 广播用户加入消息
    join_msg = WebSocketMessage(
        type="user_joined",
        data={"user_id": client_id, "count": len(manager.active_connections)},
    )
    await manager.broadcast(join_msg, exclude_client=client_id)
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            msg_data = json.loads(data)
            
            # 创建消息对象
            message = WebSocketMessage(
                type=msg_data.get("type", "message"),
                data=msg_data.get("data"),
                client_id=client_id
            )
            
            # 根据消息类型处理
            if message.type == "chat":
                # 广播聊天消息
                await manager.broadcast(message)
            elif message.type == "private":
                # 发送私人消息
                recipient_id = msg_data.get("recipient_id")
                await manager.send_personal(recipient_id, message)
            elif message.type == "ping":
                # 响应 ping
                pong_msg = WebSocketMessage(
                    type="pong",
                    data={"timestamp": message.timestamp},
                    client_id=client_id
                )
                await manager.send_personal(client_id, pong_msg)
    
    except WebSocketDisconnect:
        # 断开连接
        await manager.disconnect(client_id)
        
        # 广播用户离开消息
        leave_msg = WebSocketMessage(
            type="user_left",
            data={"user_id": client_id, "count": len(manager.active_connections)},
        )
        await manager.broadcast(leave_msg)

@app.get("/")
async def get():
    """返回主页"""
    return {"message": "WebSocket server is running"}

@app.get("/clients")
async def get_clients():
    """获取连接的客户端列表"""
    return {
        "count": len(manager.active_connections),
        "clients": list(manager.active_connections.keys())
    }
```

### 2. 创建前端页面

**static/index.html**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Chat</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
        }
        #messages {
            border: 1px solid #ccc;
            height: 300px;
            overflow-y: auto;
            padding: 10px;
            margin-bottom: 10px;
        }
        .message {
            margin: 5px 0;
            padding: 5px;
            background-color: #f0f0f0;
            border-radius: 5px;
        }
        .message.sent {
            background-color: #e3f2fd;
            text-align: right;
        }
        #input {
            width: 100%;
            padding: 10px;
            font-size: 16px;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h1>WebSocket Chat</h1>
    <div id="messages"></div>
    <input type="text" id="input" placeholder="Enter message...">
    <button onclick="sendMessage()">Send</button>

    <script>
        const clientId = 'client_' + Math.random().toString(36).substr(2, 9);
        const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}`);
        const messagesDiv = document.getElementById('messages');
        const inputField = document.getElementById('input');

        ws.onopen = function(event) {
            console.log('Connected to server');
            addMessage('System', 'Connected to server', 'system');
        };

        ws.onmessage = function(event) {
            const msg = JSON.parse(event.data);
            addMessage(msg.client_id || 'Server', JSON.stringify(msg.data), msg.type);
        };

        ws.onerror = function(event) {
            console.error('WebSocket error:', event);
            addMessage('System', 'Error occurred', 'error');
        };

        ws.onclose = function(event) {
            console.log('Disconnected from server');
            addMessage('System', 'Disconnected from server', 'system');
        };

        function sendMessage() {
            const text = inputField.value;
            if (text.trim() === '') return;

            const message = {
                type: 'chat',
                data: { text: text }
            };

            ws.send(JSON.stringify(message));
            addMessage('You', text, 'sent');
            inputField.value = '';
        }

        function addMessage(sender, text, type) {
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message ' + type;
            msgDiv.innerHTML = `<strong>${sender}:</strong> ${text}`;
            messagesDiv.appendChild(msgDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        inputField.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    </script>
</body>
</html>
```

---

## 消息类型

### 系统消息

```python
# 用户加入
user_joined = WebSocketMessage(
    type="user_joined",
    data={"user_id": "client_1", "count": 5}
)

# 用户离开
user_left = WebSocketMessage(
    type="user_left",
    data={"user_id": "client_1", "count": 4}
)
```

### 聊天消息

```python
# 公开消息
chat_msg = WebSocketMessage(
    type="chat",
    data={"text": "Hello everyone!", "user_id": "client_1"},
    client_id="client_1"
)

# 私人消息
private_msg = WebSocketMessage(
    type="private",
    data={"text": "Hello!", "recipient_id": "client_2"},
    client_id="client_1"
)
```

### 控制消息

```python
# Ping/Pong
ping_msg = WebSocketMessage(
    type="ping",
    data={"timestamp": "2024-11-28T10:30:45"}
)

pong_msg = WebSocketMessage(
    type="pong",
    data={"timestamp": "2024-11-28T10:30:45"}
)
```

---

## 高级功能

### 1. 房间管理

```python
class RoomManager:
    def __init__(self):
        self.rooms = {}
    
    async def create_room(self, room_id: str):
        self.rooms[room_id] = {}
    
    async def join_room(self, room_id: str, client_id: str, websocket):
        if room_id not in self.rooms:
            await self.create_room(room_id)
        self.rooms[room_id][client_id] = websocket
    
    async def broadcast_to_room(self, room_id: str, message: WebSocketMessage):
        if room_id in self.rooms:
            for client_id, websocket in self.rooms[room_id].items():
                await websocket.send_json(message.to_dict())
```

### 2. 消息处理器

```python
class MessageHandler:
    def __init__(self):
        self.handlers = {}
    
    def register(self, msg_type: str, handler):
        self.handlers[msg_type] = handler
    
    async def handle(self, message: WebSocketMessage):
        handler = self.handlers.get(message.type)
        if handler:
            return await handler(message)
```

### 3. 心跳检测

```python
import asyncio

async def heartbeat(websocket, interval=30):
    """定期发送心跳"""
    while True:
        try:
            await asyncio.sleep(interval)
            ping_msg = WebSocketMessage(type="ping", data={})
            await websocket.send_json(ping_msg.to_dict())
        except Exception as e:
            print(f"Heartbeat error: {e}")
            break
```

---

## 最佳实践

### 1. 错误处理

```python
try:
    while True:
        data = await websocket.receive_text()
        # 处理消息
except WebSocketDisconnect:
    # 处理断开连接
    await manager.disconnect(client_id)
except Exception as e:
    # 处理其他错误
    print(f"Error: {e}")
```

### 2. 消息验证

```python
from pydantic import BaseModel, ValidationError

class ChatMessage(BaseModel):
    type: str
    data: dict

async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = ChatMessage(**json.loads(data))
            # 处理验证后的消息
    except ValidationError as e:
        await websocket.send_json({"error": str(e)})
```

### 3. 连接超时

```python
import asyncio

async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    
    try:
        while True:
            # 30 秒超时
            data = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=30.0
            )
            # 处理消息
    except asyncio.TimeoutError:
        await websocket.close(code=1000, reason="Timeout")
```

---

## 常见问题

**Q: WebSocket 和 HTTP 长轮询有什么区别？**

A: WebSocket 是真正的双向通信，而长轮询是客户端不断向服务器发送请求。WebSocket 更高效。

**Q: 如何处理 WebSocket 连接断开？**

A: 使用 `WebSocketDisconnect` 异常捕获断开事件，然后清理资源。

**Q: 如何扩展到多个服务器？**

A: 使用消息队列（如 Redis）在服务器间传递消息。

---

## 相关资源

- [WebSocket 官方规范](https://tools.ietf.org/html/rfc6455)
- [FastAPI WebSocket 文档](https://fastapi.tiangolo.com/advanced/websockets/)
- [WebSocket 最佳实践](https://www.ably.io/topic/websockets)

---

**下一步**: [CLI 工具](20-cli.md) →
