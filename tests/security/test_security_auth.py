#!/usr/bin/env python3
"""
Security tests for authentication and authorization
Tests JWT tokens, RBAC, and security edge cases
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.auth import AuthenticationManager, SessionManager
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.authorization import (
    AuthorizationManager,
    Permission,
    Role,
    User,
    require_permission,
    require_any_permission,
)


class TestAuthentication:
    """Test authentication functionality"""

    def setup_method(self):
        """Setup for each test"""
        self.auth_mgr = AuthenticationManager()
        self.session_mgr = SessionManager()

    @pytest.mark.timeout(15)
    def test_token_generation(self):
        """Test JWT token generation"""
        # Generate token
        token = self.auth_mgr.generate_token(
            user_id="test123", email="test@example.com", role="editor"
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.timeout(15)
    def test_token_verification(self):
        """Test JWT token verification"""
        # Generate and verify token
        token = self.auth_mgr.generate_token(
            user_id="test123", email="test@example.com", role="editor"
        )

        payload = self.auth_mgr.verify_token(token)

        assert payload is not None
        assert payload["user_id"] == "test123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "editor"

    @pytest.mark.timeout(15)
    def test_invalid_token(self):
        """Test invalid token handling"""
        # Test malformed token
        assert self.auth_mgr.verify_token("invalid.token.here") is None

        # Test empty token
        assert self.auth_mgr.verify_token("") is None

        # Test None token
        assert self.auth_mgr.verify_token(None) is None

    @pytest.mark.timeout(15)
    def test_expired_token(self):
        """Test expired token handling"""
        # Create expired token by manipulating time
        self.auth_mgr.token_expiry_hours = -1  # Expire immediately
        token = self.auth_mgr.generate_token("test123")

        # Reset expiry
        self.auth_mgr.token_expiry_hours = 24

        # Verify should fail
        assert self.auth_mgr.verify_token(token) is None

    @pytest.mark.timeout(15)
    def test_token_refresh(self):
        """Test token refresh functionality"""
        # Generate initial token
        token1 = self.auth_mgr.generate_token(
            user_id="test123", email="test@example.com", role="viewer"
        )

        # Small delay to ensure different timestamp
        time.sleep(0.001)

        # Refresh token
        token2 = self.auth_mgr.refresh_token(token1)

        assert token2 is not None
        assert token2 != token1  # Should be different

        # Verify new token
        payload = self.auth_mgr.verify_token(token2)
        assert payload["user_id"] == "test123"
        assert payload["role"] == "viewer"

    @pytest.mark.timeout(15)
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "SuperSecure123!"

        # Hash password
        hashed = self.auth_mgr.hash_password(password)
        assert hashed != password  # Should be hashed
        assert len(hashed) == 64  # SHA-256 hex length

        # Verify correct password
        assert self.auth_mgr.verify_password(password, hashed) is True

        # Verify wrong password
        assert self.auth_mgr.verify_password("WrongPassword", hashed) is False

    @pytest.mark.timeout(15)
    def test_bearer_token_extraction(self):
        """Test bearer token extraction from headers"""
        # Valid bearer token
        token = self.auth_mgr.extract_bearer_token("Bearer abc123xyz")
        assert token == "abc123xyz"

        # No bearer prefix
        assert self.auth_mgr.extract_bearer_token("abc123xyz") is None

        # Empty header
        assert self.auth_mgr.extract_bearer_token("") is None

        # Just "Bearer"
        assert self.auth_mgr.extract_bearer_token("Bearer") is None

    @pytest.mark.timeout(15)
    def test_session_management(self):
        """Test session management"""
        user_id = "user123"
        token = "token123"

        # Create session
        self.session_mgr.create_session(user_id, token)
        assert user_id in self.session_mgr.active_sessions

        # Update activity
        time.sleep(0.1)
        self.session_mgr.update_activity(user_id)
        session = self.session_mgr.active_sessions[user_id]
        assert session["last_activity"] > session["created_at"]

        # Blacklist token
        self.session_mgr.invalidate_token(token)
        assert self.session_mgr.is_token_blacklisted(token) is True

        # Cleanup expired sessions
        self.session_mgr.cleanup_expired_sessions(expiry_hours=0)
        assert user_id not in self.session_mgr.active_sessions


class TestAuthorization:
    """Test authorization functionality"""

    def setup_method(self):
        """Setup for each test"""
        self.auth_mgr = AuthorizationManager()

    @pytest.mark.timeout(15)
    def test_role_permissions(self):
        """Test role-based permissions"""
        # Admin should have all permissions
        admin_perms = self.auth_mgr.get_role_permissions("admin")
        assert Permission.MANAGE_USERS in admin_perms
        assert Permission.DELETE_ENTRIES in admin_perms
        assert Permission.SYSTEM_CONFIG in admin_perms

        # Editor should have limited permissions
        editor_perms = self.auth_mgr.get_role_permissions("editor")
        assert Permission.WRITE_ENTRIES in editor_perms
        assert Permission.MANAGE_USERS not in editor_perms

        # Viewer should have read-only
        viewer_perms = self.auth_mgr.get_role_permissions("viewer")
        assert Permission.READ_ENTRIES in viewer_perms
        assert Permission.WRITE_ENTRIES not in viewer_perms

    @pytest.mark.timeout(15)
    def test_permission_checking(self):
        """Test permission checking"""
        # Admin can do everything
        assert (
            self.auth_mgr.check_permission("admin", Permission.DELETE_ENTRIES) is True
        )
        assert self.auth_mgr.check_permission("admin", Permission.MANAGE_USERS) is True

        # Editor cannot manage users
        assert (
            self.auth_mgr.check_permission("editor", Permission.WRITE_ENTRIES) is True
        )
        assert (
            self.auth_mgr.check_permission("editor", Permission.MANAGE_USERS) is False
        )

        # Viewer cannot write
        assert self.auth_mgr.check_permission("viewer", Permission.READ_ENTRIES) is True
        assert (
            self.auth_mgr.check_permission("viewer", Permission.WRITE_ENTRIES) is False
        )

    @pytest.mark.timeout(15)
    def test_multiple_permissions(self):
        """Test checking multiple permissions"""
        # Check all required
        assert (
            self.auth_mgr.check_multiple_permissions(
                "editor",
                [Permission.READ_ENTRIES, Permission.WRITE_ENTRIES],
                require_all=True,
            )
            is True
        )

        assert (
            self.auth_mgr.check_multiple_permissions(
                "editor",
                [Permission.WRITE_ENTRIES, Permission.MANAGE_USERS],
                require_all=True,
            )
            is False
        )

        # Check any required
        assert (
            self.auth_mgr.check_multiple_permissions(
                "viewer",
                [Permission.READ_ENTRIES, Permission.WRITE_ENTRIES],
                require_all=False,
            )
            is True
        )

    @pytest.mark.timeout(15)
    def test_invalid_role(self):
        """Test invalid role handling"""
        assert (
            self.auth_mgr.check_permission("invalid_role", Permission.READ_ENTRIES)
            is False
        )
        assert len(self.auth_mgr.get_role_permissions("invalid_role")) == 0

    @pytest.mark.timeout(15)
    def test_resource_permissions(self):
        """Test resource-specific permissions"""
        resource_id = "entry_123"
        user_id = "user_456"

        # Grant permission
        self.auth_mgr.add_resource_permission(
            resource_id, user_id, [Permission.UPDATE_ENTRIES]
        )

        # Check permission
        assert (
            self.auth_mgr.check_resource_permission(
                resource_id, user_id, Permission.UPDATE_ENTRIES
            )
            is True
        )

        assert (
            self.auth_mgr.check_resource_permission(
                resource_id, user_id, Permission.DELETE_ENTRIES
            )
            is False
        )

        # Remove permission
        self.auth_mgr.remove_resource_permissions(resource_id, user_id)
        assert (
            self.auth_mgr.check_resource_permission(
                resource_id, user_id, Permission.UPDATE_ENTRIES
            )
            is False
        )

    @pytest.mark.timeout(15)
    def test_user_class(self):
        """Test User class functionality"""
        user = User(user_id="test123", email="test@example.com", role="editor")

        # Check permissions
        assert user.has_permission(Permission.WRITE_ENTRIES) is True
        assert user.has_permission(Permission.MANAGE_USERS) is False

        # Get all permissions
        perms = user.get_permissions()
        assert Permission.READ_ENTRIES in perms
        assert Permission.WRITE_ENTRIES in perms
        assert Permission.MANAGE_USERS not in perms


class TestSecurityDecorators:
    """Test security decorators"""

    @require_permission(Permission.WRITE_ENTRIES)
    async def protected_write(self, user: User, data: str) -> str:
        return f"Written: {data}"

    @require_any_permission(Permission.DELETE_ENTRIES, Permission.UPDATE_ENTRIES)
    async def protected_modify(self, user: User, data: str) -> str:
        return f"Modified: {data}"

    @pytest.mark.asyncio
    async def test_permission_decorator_success(self):
        """Test permission decorator with valid permissions"""
        editor = User("ed1", "editor@test.com", "editor")

        # Editor can write
        result = await self.protected_write(editor, "test data")
        assert result == "Written: test data"

        # Editor can update
        result = await self.protected_modify(editor, "test data")
        assert result == "Modified: test data"

    @pytest.mark.asyncio
    async def test_permission_decorator_failure(self):
        """Test permission decorator with invalid permissions"""
        viewer = User("v1", "viewer@test.com", "viewer")

        # Viewer cannot write
        with pytest.raises(PermissionError):
            await self.protected_write(viewer, "test data")

        # Viewer cannot modify
        with pytest.raises(PermissionError):
            await self.protected_modify(viewer, "test data")

    @pytest.mark.asyncio
    async def test_permission_decorator_no_user(self):
        """Test permission decorator without user"""
        # No user provided
        with pytest.raises(PermissionError):
            await self.protected_write(None, "test data")


class TestSecurityEdgeCases:
    """Test security edge cases and attack scenarios"""

    def setup_method(self):
        """Setup for each test"""
        self.auth_mgr = AuthenticationManager()

    @pytest.mark.timeout(15)
    def test_sql_injection_in_token(self):
        """Test SQL injection attempts in token"""
        # Generate token with SQL injection attempt
        token = self.auth_mgr.generate_token(
            user_id="'; DROP TABLE users; --", email="test@test.com"
        )

        # Should handle safely
        payload = self.auth_mgr.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "'; DROP TABLE users; --"

    @pytest.mark.timeout(15)
    def test_large_token_payload(self):
        """Test handling of large token payloads"""
        # Create large user ID
        large_id = "A" * 10000

        # Should handle without issues
        token = self.auth_mgr.generate_token(user_id=large_id)
        payload = self.auth_mgr.verify_token(token)

        assert payload["user_id"] == large_id

    @pytest.mark.timeout(15)
    def test_token_tampering(self):
        """Test token tampering detection"""
        token = self.auth_mgr.generate_token("test123")

        # Tamper with token (change a character)
        if len(token) > 10:
            tampered = token[:10] + "X" + token[11:]
            assert self.auth_mgr.verify_token(tampered) is None

    @pytest.mark.timeout(15)
    def test_timing_attack_resistance(self):
        """Test resistance to timing attacks"""
        password = "TestPassword123"
        wrong_password = "WrongPassword456"
        hashed = self.auth_mgr.hash_password(password)

        # Time correct password verification
        start = time.time()
        for _ in range(100):
            self.auth_mgr.verify_password(password, hashed)
        correct_time = time.time() - start

        # Time wrong password verification
        start = time.time()
        for _ in range(100):
            self.auth_mgr.verify_password(wrong_password, hashed)
        wrong_time = time.time() - start

        # Times should be similar (within 20%)
        time_ratio = correct_time / wrong_time
        assert 0.8 < time_ratio < 1.2


def main():
    """Run all security tests"""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    main()
