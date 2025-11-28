"""
示例 8: 使用资源检查器

演示如何使用资源检查器进行资源级权限控制。
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

app = FastAPI(title="资源检查器示例")

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
# 2. 定义资源映射
# ============================================================================

RESOURCES_MAP = {
    "post_1": {
        "owner_id": "user1",
        "title": "First Post",
        "content": "This is the first post",
        "permissions": {
            "user2": ["read"],
            "user3": ["read", "comment"],
        },
    },
    "post_2": {
        "owner_id": "user2",
        "title": "Second Post",
        "content": "This is the second post",
        "permissions": {
            "user1": ["read"],
            "user3": ["read", "comment"],
        },
    },
    "post_3": {
        "owner_id": "user3",
        "title": "Third Post",
        "content": "This is the third post",
        "permissions": {
            "user1": ["read"],
            "user2": ["read"],
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


@app.get("/posts")
async def list_posts(current_user: dict = Depends(get_current_user)):
    """列出所有文章"""
    posts = []
    for post_id, post in RESOURCES_MAP.items():
        # 检查用户是否可以读取此文章
        can_read = await engine.check_permission(
            current_user["user_id"],
            "read",
            resource_id=post_id,
        )

        if can_read:
            posts.append({
                "id": post_id,
                "title": post["title"],
                "owner": post["owner_id"],
            })

    return {"posts": posts}


@app.get("/posts/{post_id}")
async def get_post(
    post_id: str,
    current_user: dict = Depends(require_permission("read")),
):
    """获取单个文章"""
    if post_id not in RESOURCES_MAP:
        raise HTTPException(status_code=404, detail="Post not found")

    # 检查资源权限
    can_read = await engine.check_permission(
        current_user["user_id"],
        "read",
        resource_id=post_id,
    )

    if not can_read:
        raise HTTPException(status_code=403, detail="No permission to read this post")

    post = RESOURCES_MAP[post_id]
    return {
        "id": post_id,
        "title": post["title"],
        "content": post["content"],
        "owner": post["owner_id"],
    }


@app.put("/posts/{post_id}")
async def update_post(
    post_id: str,
    title: str,
    content: str,
    current_user: dict = Depends(require_permission("write")),
):
    """更新文章 - 只有所有者可以更新"""
    if post_id not in RESOURCES_MAP:
        raise HTTPException(status_code=404, detail="Post not found")

    # 检查所有权
    is_owner = await cached_checker.check_owner(
        current_user["user_id"],
        post_id,
    )

    if not is_owner:
        raise HTTPException(status_code=403, detail="Only owner can update this post")

    # 更新文章
    RESOURCES_MAP[post_id]["title"] = title
    RESOURCES_MAP[post_id]["content"] = content

    return {
        "id": post_id,
        "title": title,
        "content": content,
        "status": "updated",
    }


@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    current_user: dict = Depends(require_permission("delete")),
):
    """删除文章 - 只有所有者可以删除"""
    if post_id not in RESOURCES_MAP:
        raise HTTPException(status_code=404, detail="Post not found")

    # 检查所有权
    is_owner = await cached_checker.check_owner(
        current_user["user_id"],
        post_id,
    )

    if not is_owner:
        raise HTTPException(status_code=403, detail="Only owner can delete this post")

    # 删除文章
    del RESOURCES_MAP[post_id]

    return {
        "id": post_id,
        "status": "deleted",
    }


@app.post("/posts/{post_id}/share")
async def share_post(
    post_id: str,
    target_user: str,
    permission: str,
    current_user: dict = Depends(require_permission("write")),
):
    """与其他用户共享文章"""
    if post_id not in RESOURCES_MAP:
        raise HTTPException(status_code=404, detail="Post not found")

    # 检查所有权
    is_owner = await cached_checker.check_owner(
        current_user["user_id"],
        post_id,
    )

    if not is_owner:
        raise HTTPException(status_code=403, detail="Only owner can share this post")

    # 添加权限
    if target_user not in RESOURCES_MAP[post_id]["permissions"]:
        RESOURCES_MAP[post_id]["permissions"][target_user] = []

    if permission not in RESOURCES_MAP[post_id]["permissions"][target_user]:
        RESOURCES_MAP[post_id]["permissions"][target_user].append(permission)

    # 清理缓存
    cached_checker.clear_cache(f"*{post_id}*")

    return {
        "post_id": post_id,
        "target_user": target_user,
        "permission": permission,
        "status": "shared",
    }


@app.get("/posts/{post_id}/check-permission/{permission}")
async def check_post_permission(
    post_id: str,
    permission: str,
    current_user: dict = Depends(get_current_user),
):
    """检查用户对文章的权限"""
    if post_id not in RESOURCES_MAP:
        raise HTTPException(status_code=404, detail="Post not found")

    has_permission = await engine.check_permission(
        current_user["user_id"],
        permission,
        resource_id=post_id,
    )

    is_owner = await cached_checker.check_owner(
        current_user["user_id"],
        post_id,
    )

    return {
        "post_id": post_id,
        "user": current_user["user_id"],
        "permission": permission,
        "has_permission": has_permission,
        "is_owner": is_owner,
    }


# ============================================================================
# 8. 测试用例
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("资源检查器示例")
    print("=" * 50)
    print("\n测试用户:")
    for user, perms in PERMISSIONS_MAP.items():
        print(f"  {user}: {perms}")

    print("\n\n测试资源:")
    for post_id, post in RESOURCES_MAP.items():
        print(f"  {post_id}: owner={post['owner_id']}, title={post['title']}")

    print("\n\n启动服务器...")
    print("访问 http://localhost:8000/docs 查看 API 文档")
    print("\n测试步骤:")
    print("1. 使用 POST /login 登录")
    print("2. 复制返回的 access_token")
    print("3. 在 Swagger UI 中点击 'Authorize' 按钮")
    print("4. 输入: Bearer <access_token>")
    print("5. 测试各个端点")

    uvicorn.run(app, host="0.0.0.0", port=8000)
