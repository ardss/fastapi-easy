# Security Guide for FastAPI-Easy

This document outlines the security features and best practices for FastAPI-Easy.

## Overview

FastAPI-Easy includes comprehensive security enhancements to protect your applications from common vulnerabilities. The security framework follows OWASP best practices and implements defense-in-depth strategies.

## Security Features

### 1. Authentication & Authorization

#### JWT Authentication (Enhanced)
- **Token Security**: Uses PBKDF2 key derivation for secret keys
- **Algorithm Support**: Supports HS256 and RS256 algorithms
- **Token Claims**: Includes jti (JWT ID), nbf (not before), issuer, and audience validation
- **Rate Limiting**: Limits token creation and verification attempts
- **Blacklisting**: Supports token revocation and blacklisting

```python
from fastapi_easy.security import JWTAuth

# Enhanced JWT configuration
jwt_auth = JWTAuth(
    algorithm="RS256",  # Use asymmetric encryption in production
    access_token_expire_minutes=15,
    issuer="your-app",
    audience="your-users",
    require_issuer=True,
    require_audience=True,
)
```

#### Password Security
- **Multiple Algorithms**: Supports Argon2id (recommended) and bcrypt
- **Password Strength**: Comprehensive password strength validation
- **Rate Limiting**: Prevents brute force attacks
- **Pepper Support**: Additional secret layer for password hashing

```python
from fastapi_easy.security import PasswordManager

# Enhanced password manager
password_manager = PasswordManager(
    algorithm="argon2",  # Argon2id is recommended
    argon2_time_cost=3,
    argon2_memory_cost=65536,
    argon2_parallelism=4,
)
```

### 2. Input Validation & Sanitization

#### Comprehensive Validation
- **SQL Injection Prevention**: Validates all SQL query parameters
- **XSS Protection**: Sanitizes and escapes HTML content
- **Path Traversal Protection**: Validates file system paths
- **Command Injection Prevention**: Validates system commands
- **Input Length Limits**: Prevents buffer overflow attacks

```python
from fastapi_easy.security.validation import SecurityValidator

# Validate input
sanitized_data = SecurityValidator.comprehensive_validation(user_input)
```

#### Pydantic Validators
- Pre-built validators for common security checks
- Email validation with security checks
- Password strength validation
- Field name sanitization

### 3. Security Middleware

#### SecurityMiddleware Features
- **Rate Limiting**: IP-based rate limiting with configurable thresholds
- **IP Blacklisting**: Automatic IP blacklisting for abusive clients
- **Security Headers**: Adds comprehensive security headers to responses
- **CORS Protection**: Configurable CORS with secure defaults
- **Request Size Limits**: Prevents large payload attacks

```python
from fastapi_easy.security.middleware import SecurityMiddleware

# Add security middleware
app.add_middleware(
    SecurityMiddleware,
    jwt_auth=jwt_auth,
    rate_limit_per_minute=60,
    max_request_size=10_000_000,  # 10MB
    enable_input_validation=True,
)
```

### 4. Database Security

#### SQL Injection Prevention
- **Parameterized Queries**: All database queries use parameters
- **ORM Protection**: SQLAlchemy adapters with built-in protection
- **Field Validation**: Validates all field names and values
- **Operator Restrictions**: Limits allowed SQL operators

### 5. Dependency Security

#### Vulnerability Scanning
- **Automated Scanning**: Checks for known vulnerabilities
- **Security Advisories**: Maintains database of vulnerable packages
- **Version Pinning**: Recommends specific safe versions
- **Blacklisted Packages**: Identifies and warns about insecure packages

```python
from fastapi_easy.security import DependencyChecker

# Scan for vulnerabilities
checker = DependencyChecker()
report = checker.generate_report()
print(f"Security Score: {report['security_score']}")
```

### 6. Security Logging

#### Comprehensive Logging
- **Structured Logging**: JSON format for easy parsing
- **Security Events**: Logs all security-related events
- **Sensitive Data Redaction**: Automatically redacts sensitive information
- **Log Rotation**: Prevents log file size issues
- **Metric Collection**: Provides security metrics

```python
from fastapi_easy.security.audit import SecurityLogger, SecurityEventType

# Log security events
logger = SecurityLogger()
logger.log_authentication_event(
    SecurityEventType.LOGIN_SUCCESS,
    user_id="user123",
    ip_address="192.168.1.1",
    success=True
)
```

## Configuration

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key-here
JWT_ISSUER=your-app-name
JWT_AUDIENCE=your-users
JWT_KEY_SALT=your-key-salt-here

# Security Configuration
SECURITY_LOG_LEVEL=INFO
SECURITY_LOG_FILE=logs/security.log
ENABLE_SECURITY_MIDDLEWARE=true
RATE_LIMIT_PER_MINUTE=60
```

### Security Checklist

#### Production Deployment

- [ ] Use HTTPS/TLS encryption
- [ ] Set secure cookies (HttpOnly, Secure, SameSite)
- [ ] Configure proper CORS origins
- [ ] Enable security headers
- [ ] Use asymmetric encryption for JWT (RS256)
- [ ] Set up log monitoring and alerts
- [ ] Implement intrusion detection
- [ ] Regular security updates
- [ ] Security testing in CI/CD pipeline

#### Development

- [ ] Never commit secrets or keys
- [ ] Use environment variables for configuration
- [ ] Enable all security middleware in development
- [ ] Test with security scanners
- [ ] Regular dependency updates
- [ ] Code review for security issues

## Security Best Practices

### 1. Authentication
- Use strong password policies
- Implement multi-factor authentication
- Use short-lived access tokens
- Implement proper logout functionality
- Monitor for suspicious login attempts

### 2. Data Protection
- Encrypt sensitive data at rest
- Use TLS for data in transit
- Implement data access controls
- Regular data backup and recovery
- Comply with data protection regulations

### 3. API Security
- Validate all inputs
- Use rate limiting
- Implement API keys for public APIs
- Version your APIs
- Document security requirements

### 4. Monitoring & Alerting
- Monitor failed login attempts
- Alert on security violations
- Regular security audits
- Penetration testing
- Vulnerability scanning

## Common Vulnerabilities & Protections

### OWASP Top 10 Coverage

1. **Broken Access Control**
   - Proper authorization checks
   - Role-based access control
   - Secure direct object references

2. **Cryptographic Failures**
   - Strong encryption algorithms
   - Proper key management
   - Secure password storage

3. **Injection**
   - Parameterized queries
   - Input validation
   - ORM usage

4. **Insecure Design**
   - Security by design
   - Threat modeling
   - Secure defaults

5. **Security Misconfiguration**
   - Secure defaults
   - Configuration validation
   - Regular updates

6. **Vulnerable Components**
   - Dependency scanning
   - Version management
   - Security patches

7. **Authentication Failures**
   - Strong authentication
   - Session management
   - Multi-factor auth

8. **Software and Data Integrity**
   - Code signing
   - Secure updates
   - CI/CD security

9. **Logging & Monitoring**
   - Comprehensive logging
   - Security monitoring
   - Incident response

10. **Server-Side Request Forgery**
    - URL validation
    - Allow-list approach
    - Network segmentation

## Security Tools Integration

### CI/CD Pipeline

```yaml
# Example GitHub Actions workflow
- name: Security Scan
  run: |
    python -m fastapi_easy.security.dependency_checker

- name: Security Tests
  run: |
    pytest tests/security/

- name: Static Analysis
  run: |
    bandit -r src/
    safety check
```

### Monitoring Tools

- **ELK Stack**: For log analysis
- **Prometheus**: For metrics collection
- **Grafana**: For security dashboards
- **Fail2ban**: For IP blocking
- **WAF**: Web Application Firewall

## Incident Response

### Security Incident Procedure

1. **Detection**
   - Monitor security logs
   - Set up alerts
   - Anomaly detection

2. **Containment**
   - Isolate affected systems
   - Block malicious IPs
   - Revoke compromised tokens

3. **Investigation**
   - Analyze logs
   - Identify root cause
   - Assess impact

4. **Recovery**
   - Patch vulnerabilities
   - Update systems
   - Monitor for recurrence

5. **Lessons Learned**
   - Document findings
   - Update procedures
   - Improve defenses

## Additional Resources

- [OWASP Security Guide](https://owasp.org/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Security Guide](https://python-security.readthedocs.io/)
- [JWT Handbook](https://jwt.io/introduction/)
- [Argon2 Password Hashing](https://github.com/hydephant/argon2-cffi)

## Support

For security-related questions or to report vulnerabilities:
- Create an issue with "SECURITY" label
- Email: security@fastapi-easy.com
- Follow responsible disclosure practices