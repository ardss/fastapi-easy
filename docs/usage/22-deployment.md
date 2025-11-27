# 部署指南

本指南介绍如何部署使用 fastapi-easy 构建的应用。

---

## Docker 部署

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db/dbname
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=dbname
```

---

## 环境配置

### .env.production

```bash
DATABASE_URL=postgresql://user:password@host/dbname
LOG_LEVEL=WARNING
CACHE_BACKEND=redis
RATE_LIMIT_ENABLED=true
```

---

## 健康检查

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": await check_database(),
        "cache": await check_cache()
    }
```

---

## 监控

```python
@app.on_event("startup")
async def startup():
    logger.info("Application started")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutting down")
    await db.close()
```

---

**下一步**: [故障排除](23-troubleshooting.md) →
