"""
示例工具模块

提供便利函数，帮助示例自动处理常见问题。

功能:
    - 自动查找可用端口
    - 自动启动服务器
    - 自动打开浏览器
"""

import socket
import sys
from typing import Optional
import webbrowser
import time


def find_available_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    """
    查找可用的端口
    
    从指定的起始端口开始，逐个检查端口是否可用。
    如果端口被占用，自动尝试下一个端口。
    
    参数:
        start_port: 起始端口号 (默认: 8000)
        max_attempts: 最多尝试次数 (默认: 100)
    
    返回:
        可用的端口号
    
    异常:
        RuntimeError: 如果找不到可用端口
    
    示例:
        >>> port = find_available_port()
        >>> print(f"使用端口: {port}")
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            # 尝试创建 socket 并绑定到该端口
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", port))
            sock.close()
            return port
        except OSError:
            # 端口被占用，继续尝试下一个
            continue
    
    # 如果找不到可用端口，抛出异常
    raise RuntimeError(
        f"无法找到可用端口 (尝试了 {start_port} 到 {start_port + max_attempts - 1})"
    )


def run_app(
    app,
    host: str = "127.0.0.1",
    start_port: int = 8000,
    reload: bool = True,
    open_browser: bool = True,
    auto_port: bool = True,
):
    """
    运行 FastAPI 应用，自动处理端口占用问题
    
    参数:
        app: FastAPI 应用实例
        host: 绑定的主机地址 (默认: 127.0.0.1)
        start_port: 起始端口号 (默认: 8000)
        reload: 是否启用自动重载 (默认: True)
        open_browser: 是否自动打开浏览器 (默认: True)
        auto_port: 是否自动查找可用端口 (默认: True)
    
    示例:
        >>> from fastapi import FastAPI
        >>> from examples.utils import run_app
        >>> 
        >>> app = FastAPI()
        >>> 
        >>> @app.get("/")
        >>> async def root():
        ...     return {"message": "Hello"}
        >>> 
        >>> if __name__ == "__main__":
        ...     run_app(app)
    """
    import uvicorn
    
    # 自动查找可用端口
    if auto_port:
        port = find_available_port(start_port)
        if port != start_port:
            print(f"[WARNING] 端口 {start_port} 被占用，自动使用端口 {port}")
    else:
        port = start_port
    
    url = f"http://{host}:{port}"
    
    print(f"\n{'='*60}")
    print(f"[INFO] FastAPI 应用启动")
    print(f"{'='*60}")
    print(f"[INFO] 地址: {url}")
    print(f"[INFO] API 文档: {url}/docs")
    print(f"[INFO] ReDoc: {url}/redoc")
    print(f"{'='*60}\n")
    
    # 自动打开浏览器
    if open_browser:
        # 延迟打开浏览器，确保服务器已启动
        def open_browser_later():
            time.sleep(2)
            try:
                webbrowser.open(f"{url}/docs")
                print(f"[INFO] 已打开浏览器: {url}/docs\n")
            except Exception as e:
                print(f"[WARNING] 无法打开浏览器: {e}\n")
        
        import threading
        thread = threading.Thread(target=open_browser_later, daemon=True)
        thread.start()
    
    # 启动 Uvicorn 服务器
    # 注意: 当使用 reload=True 时，需要传递模块路径字符串而不是应用对象
    # 但由于这里直接传递应用对象，所以禁用 reload
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,  # 直接运行时禁用 reload，避免警告
    )


def get_port_info(port: int = 8000) -> Optional[str]:
    """
    获取占用指定端口的进程信息
    
    参数:
        port: 端口号
    
    返回:
        进程信息字符串，如果端口未被占用则返回 None
    
    示例:
        >>> info = get_port_info(8000)
        >>> if info:
        ...     print(f"端口 8000 被占用: {info}")
        ... else:
        ...     print("端口 8000 可用")
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        sock.close()
        return None
    except OSError as e:
        return str(e)


# ============ 使用示例 ============

if __name__ == "__main__":
    # 示例 1: 查找可用端口
    print("示例 1: 查找可用端口")
    port = find_available_port()
    print(f"✅ 可用端口: {port}\n")
    
    # 示例 2: 检查端口状态
    print("示例 2: 检查端口状态")
    for p in [8000, 8001, 8002]:
        info = get_port_info(p)
        if info:
            print(f"❌ 端口 {p} 被占用: {info}")
        else:
            print(f"✅ 端口 {p} 可用")
