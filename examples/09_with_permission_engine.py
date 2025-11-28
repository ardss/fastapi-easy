"""
示例 9: 使用权限检查引擎

演示如何使用权限检查引擎进行复杂的权限检查。
"""

from fastapi import Depends, FastAPI, HTTPException

from fastapi_easy.security import (
    CachedResourceChecker,
    JWTAuth,
    PermissionEngine,
    SecurityConfig,
    StaticPermissionLoader,
    StaticResourceChecker,
    get_current_user,
    init_jwt_auth,
    require_permission,
)

app = FastAPI(title="权限检查引擎示例")

# ============================================================================
# 1. 定义权限映射
# ============================================================================

PERMISSIONS_MAP = {
    "user1": ["read", "write"],
    "user2": ["read"],
    "user3": ["read", "write", "delete"],
    "admin": ["read", "write", "delete", "admin", "audit"],
}

# ============================================================================
# 2. 定义资源映射
# ============================================================================

RESOURCES_MAP = {
    "report_1": {
        "owner_id": "user1",
        "title": "Sales Report",
        "permissions": {
            "user2": ["read"],
            "user3": ["read", "comment"],
        },
    },
    "report_2": {
        "owner_id": "user2",
        "title": "Marketing Report",
        "permissions": {
            "user1": ["read"],
            "user3": ["read", "comment"],
        },
    },
}

# ============================================================================
# 3. 创建权限加载器和资源检查器
# ============================================================================

permission_loader = StaticPermissionLoader(PERMISSIONS_MAP)
resource_checker = StaticResourceChecker(RESOURCES_MAP)
cached_checker = CachedResourceChecker(resource_checker, cache_ttl=300)

# ============================================================================
# 4. 创建权限引擎
# ============================================================================

engine = PermissionEngine(
    permission_loader=permission_loader,
    resource_checker=cached_checker,
    enable_cache=True,
    cache_ttl=300,
)

# ============================================================================
# 5. 创建安全配置
# ============================================================================

jwt_auth = JWTAuth(secret_key="example-secret-key-do-not-use-in-production")

config = SecurityConfig(
    jwt_auth=jwt_auth,
    permission_loader=permission_loader,
)

# ============================================================================
# 6. 初始化 JWT 认证
# ============================================================================

init_jwt_auth(secret_key="example-secret-key-do-not-use-in-production")

# ============================================================================
# 7. 定义路由
# ============================================================================


@app.post("/login")
async def login(username: str, password: str):
    """登录端点"""
    if not username:
        raise HTTPException(status_code=400, detail="Username required")

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


# ============================================================================
# 单个权限检查
# ============================================================================


@app.get("/data/read")
async def read_data(current_user: dict = Depends(get_current_user)):
    """读取数据 - 需要 read 权限"""
    has_permission = await engine.check_permission(
        current_user["user_id"],
        "read",
    )

    if not has_permission:
        raise HTTPException(status_code=403, detail="No read permission")

    return {"data": "sensitive data", "user": current_user["user_id"]}


@app.post("/data/write")
async def write_data(current_user: dict = Depends(get_current_user)):
    """写入数据 - 需要 write 权限"""
    has_permission = await engine.check_permission(
        current_user["user_id"],
        "write",
    )

    if not has_permission:
        raise HTTPException(status_code=403, detail="No write permission")

    return {"status": "data written", "user": current_user["user_id"]}


# ============================================================================
# 多权限检查 (AND)
# ============================================================================


@app.post("/data/publish")
async def publish_data(current_user: dict = Depends(get_current_user)):
    """发布数据 - 需要 read 和 write 权限"""
    has_all = await engine.check_all_permissions(
        current_user["user_id"],
        ["read", "write"],
    )

    if not has_all:
        raise HTTPException(
            status_code=403,
            detail="Need both read and write permissions",
        )

    return {"status": "data published", "user": current_user["user_id"]}


@app.delete("/data/purge")
async def purge_data(current_user: dict = Depends(get_current_user)):
    """清除数据 - 需要 delete 和 admin 权限"""
    has_all = await engine.check_all_permissions(
        current_user["user_id"],
        ["delete", "admin"],
    )

    if not has_all:
        raise HTTPException(
            status_code=403,
            detail="Need both delete and admin permissions",
        )

    return {"status": "data purged", "user": current_user["user_id"]}


# ============================================================================
# 多权限检查 (OR)
# ============================================================================


@app.get("/data/access")
async def access_data(current_user: dict = Depends(get_current_user)):
    """访问数据 - 需要 read 或 admin 权限"""
    has_any = await engine.check_any_permission(
        current_user["user_id"],
        ["read", "admin"],
    )

    if not has_any:
        raise HTTPException(
            status_code=403,
            detail="Need read or admin permission",
        )

    return {"data": "data", "user": current_user["user_id"]}


@app.post("/data/modify")
async def modify_data(current_user: dict = Depends(get_current_user)):
    """修改数据 - 需要 write 或 admin 权限"""
    has_any = await engine.check_any_permission(
        current_user["user_id"],
        ["write", "admin"],
    )

    if not has_any:
        raise HTTPException(
            status_code=403,
            detail="Need write or admin permission",
        )

    return {"status": "data modified", "user": current_user["user_id"]}


# ============================================================================
# 资源级权限检查
# ============================================================================


@app.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
):
    """获取报告 - 检查资源权限"""
    if report_id not in RESOURCES_MAP:
        raise HTTPException(status_code=404, detail="Report not found")

    # 检查资源权限
    has_permission = await engine.check_permission(
        current_user["user_id"],
        "read",
        resource_id=report_id,
    )

    if not has_permission:
        raise HTTPException(status_code=403, detail="No permission to read this report")

    report = RESOURCES_MAP[report_id]
    return {
        "id": report_id,
        "title": report["title"],
        "owner": report["owner_id"],
    }


@app.put("/reports/{report_id}")
async def update_report(
    report_id: str,
    title: str,
    current_user: dict = Depends(get_current_user),
):
    """更新报告 - 只有所有者可以更新"""
    if report_id not in RESOURCES_MAP:
        raise HTTPException(status_code=404, detail="Report not found")

    # 检查所有权
    is_owner = await cached_checker.check_owner(
        current_user["user_id"],
        report_id,
    )

    if not is_owner:
        raise HTTPException(status_code=403, detail="Only owner can update this report")

    RESOURCES_MAP[report_id]["title"] = title
    return {
        "id": report_id,
        "title": title,
        "status": "updated",
    }


# ============================================================================
# 权限检查端点
# ============================================================================


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
    permissions: str,  # 逗号分隔
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
    permissions: str,  # 逗号分隔
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
# 测试用例
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("权限检查引擎示例")
    print("=" * 50)
    print("\n测试用户:")
    for user, perms in PERMISSIONS_MAP.items():
        print(f"  {user}: {perms}")

    print("\n\n启动服务器...")
    print("访问 http://localhost:8000/docs 查看 API 文档")
    print("\n测试步骤:")
    print("1. 使用 POST /login 登录")
    print("2. 复制返回的 access_token")
    print("3. 在 Swagger UI 中点击 'Authorize' 按钮")
    print("4. 输入: Bearer <access_token>")
    print("5. 测试各个端点")

    uvicorn.run(app, host="0.0.0.0", port=8000)
