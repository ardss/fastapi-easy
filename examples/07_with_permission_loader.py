"""
示例 7: 使用权限加载器

演示如何使用权限加载器动态加载用户权限。
"""

from fastapi import Depends, FastAPI, HTTPException

from fastapi_easy.security import (
    CachedPermissionLoader,
    JWTAuth,
    PermissionEngine,
    SecurityConfig,
    StaticPermissionLoader,
    get_current_user,
    require_permission,
)

app = FastAPI(title="权限加载器示例")

# ============================================================================
# 1. 定义权限映射
# ============================================================================

PERMISSIONS_MAP = {
    "user1": ["read", "write"],
    "user2": ["read"],
    "user3": ["read", "write", "delete"],
    "admin": ["read", "write", "delete", "admin"],
}

# ============================================================================
# 2. 创建权限加载器
# ============================================================================

# 基础加载器
base_loader = StaticPermissionLoader(PERMISSIONS_MAP)

# 添加缓存
cached_loader = CachedPermissionLoader(base_loader, cache_ttl=300)

# ============================================================================
# 3. 创建权限引擎
# ============================================================================

engine = PermissionEngine(
    permission_loader=cached_loader,
    enable_cache=True,
    cache_ttl=300,
)

# ============================================================================
# 4. 创建安全配置
# ============================================================================

jwt_auth = JWTAuth(secret_key="example-secret-key-do-not-use-in-production")

config = SecurityConfig(
    jwt_auth=jwt_auth,
    permission_loader=cached_loader,
)

# ============================================================================
# 5. 初始化 JWT 认证
# ============================================================================

from fastapi_easy.security import init_jwt_auth

init_jwt_auth(secret_key="example-secret-key-do-not-use-in-production")

# ============================================================================
# 6. 定义路由
# ============================================================================


@app.post("/login")
async def login(username: str, password: str):
    """登录端点"""
    # 这里应该验证用户名和密码
    # 为了演示，我们接受任何用户名
    if not username:
        raise HTTPException(status_code=400, detail="Username required")

    # 创建 token
    token = jwt_auth.create_access_token(
        subject=username,
        roles=["user"],
        permissions=PERMISSIONS_MAP.get(username, []),
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": username,
        "permissions": PERMISSIONS_MAP.get(username, []),
    }


@app.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "user_id": current_user["user_id"],
        "permissions": current_user.get("permissions", []),
    }


@app.get("/data")
async def get_data(current_user: dict = Depends(require_permission("read"))):
    """获取数据 - 需要 read 权限"""
    return {
        "data": "This is sensitive data",
        "user": current_user["user_id"],
    }


@app.post("/data")
async def create_data(current_user: dict = Depends(require_permission("write"))):
    """创建数据 - 需要 write 权限"""
    return {
        "status": "created",
        "user": current_user["user_id"],
    }


@app.delete("/data")
async def delete_data(current_user: dict = Depends(require_permission("delete"))):
    """删除数据 - 需要 delete 权限"""
    return {
        "status": "deleted",
        "user": current_user["user_id"],
    }


@app.get("/admin")
async def admin_panel(current_user: dict = Depends(require_permission("admin"))):
    """管理面板 - 需要 admin 权限"""
    return {
        "admin_data": "Admin only data",
        "user": current_user["user_id"],
    }


@app.get("/check-permission/{permission}")
async def check_permission(
    permission: str,
    current_user: dict = Depends(get_current_user),
):
    """检查用户是否有特定权限"""
    has_permission = await engine.check_permission(
        current_user["user_id"],
        permission,
    )

    return {
        "user": current_user["user_id"],
        "permission": permission,
        "has_permission": has_permission,
    }


@app.get("/check-all-permissions")
async def check_all_permissions(
    permissions: str,  # 逗号分隔的权限列表
    current_user: dict = Depends(get_current_user),
):
    """检查用户是否有所有权限"""
    permission_list = [p.strip() for p in permissions.split(",")]

    has_all = await engine.check_all_permissions(
        current_user["user_id"],
        permission_list,
    )

    return {
        "user": current_user["user_id"],
        "permissions": permission_list,
        "has_all_permissions": has_all,
    }


@app.get("/check-any-permission")
async def check_any_permission(
    permissions: str,  # 逗号分隔的权限列表
    current_user: dict = Depends(get_current_user),
):
    """检查用户是否有任意权限"""
    permission_list = [p.strip() for p in permissions.split(",")]

    has_any = await engine.check_any_permission(
        current_user["user_id"],
        permission_list,
    )

    return {
        "user": current_user["user_id"],
        "permissions": permission_list,
        "has_any_permission": has_any,
    }


@app.post("/clear-cache/{user_id}")
async def clear_cache(user_id: str):
    """清理特定用户的缓存"""
    engine.clear_cache(user_id)
    return {"status": "cache cleared", "user": user_id}


# ============================================================================
# 7. 测试用例
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("权限加载器示例")
    print("=" * 50)
    print("\n测试用户:")
    for user, perms in PERMISSIONS_MAP.items():
        print(f"  {user}: {perms}")

    print("\n\n启动服务器...")
    print("访问 http://localhost:8000/docs 查看 API 文档")
    print("\n测试步骤:")
    print("1. 使用 POST /login 登录（用户名: user1, user2, admin 等）")
    print("2. 复制返回的 access_token")
    print("3. 在 Swagger UI 中点击 'Authorize' 按钮")
    print("4. 输入: Bearer <access_token>")
    print("5. 测试各个端点")

    uvicorn.run(app, host="0.0.0.0", port=8000)
