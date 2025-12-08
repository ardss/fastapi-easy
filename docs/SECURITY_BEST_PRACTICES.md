# Security Best Practices for FastAPI-Easy

This guide outlines security best practices when using FastAPI-Easy in production environments.

## 🔐 Authentication & Authorization

### JWT Security
```python
from fastapi_easy.security import JWTAuth

# Use strong secret keys
jwt_auth = JWTAuth(
    secret_key="your-very-strong-secret-key-here",  # Use environment variables in production
    algorithm="HS256",
    access_token_expire_minutes=15,  # Keep access tokens short-lived
    refresh_token_expire_days=7,     # Use refresh tokens for longer sessions
    issuer="your-app-name",          # Add issuer claim
    audience="your-api-users",       # Add audience claim
    require_jti=True                # Enable unique token IDs
)
```

### CSRF Protection
```python
from fastapi_easy.middleware import CSRFMiddleware
from fastapi import FastAPI

app = FastAPI()

# Add CSRF protection middleware
app.add_middleware(
    CSRFMiddleware,
    cookie_secure=True,      # Set to True in production with HTTPS
    cookie_samesite="lax",   # Prevent CSRF attacks
    cookie_httponly=False,  # Allow JavaScript to read the token
)
```

## 🛡️ Data Validation

### Input Validation
FastAPI-Easy uses Pydantic for automatic validation:

```python
from pydantic import BaseModel, EmailStr, constr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr  # Validates email format
    password: constr(min_length=8, max_length=100)  # Password constraints
    username: constr(min_length=3, max_length=50, regex="^[a-zA-Z0-9_]+$")
    age: Optional[int] = None
```

### SQL Injection Prevention
FastAPI-Easy prevents SQL injection through:

1. **Parameterized Queries**: All database operations use parameterized queries
2. **ORM Abstraction**: Direct SQL is handled safely by the ORM adapters
3. **Input Sanitization**: Pydantic models validate and sanitize inputs

## 🚀 Deployment Security

### Environment Variables
Never hardcode sensitive information:

```bash
# Use environment variables for secrets
JWT_SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@localhost/db
REDIS_URL=redis://localhost:6379
```

### HTTPS in Production
Always use HTTPS in production:

```python
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()
app.add_middleware(HTTPSRedirectMiddleware)  # Redirect HTTP to HTTPS
```

### Secure Headers
Add security headers:

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer

# Only allow requests from trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["yourdomain.com", "*.yourdomain.com"]
)
```

## 🔍 Logging & Monitoring

### Security Logging
```python
from fastapi_easy.security import audit_log

# Enable audit logging
audit_log.configure(
    log_file="security.log",
    include_sensitive_data=False,  # Never log passwords or tokens
    rotation="daily"
)
```

### Rate Limiting
```python
from fastapi_easy.security import rate_limiter

# Configure rate limiting
rate_limiter.configure(
    redis_url="redis://localhost:6379",
    default_limits={"100/minute", "1000/hour"},
    block_time=300  # Block for 5 minutes after limit exceeded
)
```

## 🏢 Multi-Tenant Security

### Data Isolation
Ensure proper data isolation in multi-tenant environments:

```python
from fastapi_easy.security import TenantIsolationMiddleware

# Enable tenant isolation
app.add_middleware(
    TenantIsolationMiddleware,
    tenant_header="X-Tenant-ID",  # Header containing tenant ID
    strict_mode=True,            # Fail fast for invalid tenants
)
```

## 📊 Performance & Security

### Connection Pooling
Configure database connection pools:

```python
from sqlalchemy import create_engine

# Configure connection pool
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600  # Recycle connections hourly
)
```

### Query Optimization
- Use pagination for large result sets
- Implement proper indexes
- Monitor query performance

## 🚨 Common Security Mistakes to Avoid

### 1. Don't Disable Validation
```python
# BAD: Never disable validation
@app.post("/users", response_model=User, include_in_schema=False)
# GOOD: Always validate inputs
@app.post("/users", response_model=User)
```

### 2. Don't Expose Internal Details
```python
# BAD: Expose internal errors
raise HTTPException(status_code=500, detail=str(error))

# GOOD: Use generic error messages
raise HTTPException(status_code=500, detail="Internal server error")
```

### 3. Don't Store Plain Text Passwords
```python
from fastapi_easy.security import password_hasher

# Always hash passwords
hashed_password = password_hasher.hash(password)
```

## 🔧 Security Checklist

### Before Deployment
- [ ] Change all default passwords and secrets
- [ ] Enable HTTPS with valid certificates
- [ ] Configure CORS properly
- [ ] Set up security headers
- [ ] Enable rate limiting
- [ ] Configure audit logging
- [ ] Test input validation
- [ ] Review error handling
- [ ] Check for sensitive data in logs
- [ ] Verify database connection security
- [ ] Test authentication and authorization
- [ ] Review dependency security updates

### Regular Maintenance
- [ ] Update dependencies regularly
- [ ] Review audit logs
- [ ] Monitor performance metrics
- [ ] Check for security advisories
- [ ] Test backup and recovery procedures
- [ ] Review user permissions

## 📞 Reporting Security Issues

If you discover a security vulnerability, please report it privately:

- Email: security@fastapi-easy.com
- Include detailed description and reproduction steps
- We'll respond within 48 hours
- We'll work with you on a coordinated disclosure

## 🔗 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [Pydantic Security Documentation](https://pydantic-docs.helpmanual.io/)
- [SQLAlchemy Security Guide](https://docs.sqlalchemy.org/en/14/core/security.html)