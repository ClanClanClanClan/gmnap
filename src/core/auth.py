"""
Authentication module for GMNAP V7
Implements JWT-based authentication for API access
"""

import os
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets


class AuthenticationManager:
    """Handles JWT token generation and verification"""

    def __init__(self):
        # Get secret key from environment or generate one
        self.secret_key = os.environ.get("GMNAP_SECRET_KEY", self._generate_secret())
        self.algorithm = "HS256"
        self.token_expiry_hours = 24

    def _generate_secret(self) -> str:
        """Generate a secure secret key"""
        return secrets.token_urlsafe(32)

    def generate_token(self, user_id: str, email: str = None, role: str = "viewer") -> str:
        """
        Generate a JWT token for a user

        Args:
            user_id: Unique user identifier
            email: User email (optional)
            role: User role (admin, editor, viewer)

        Returns:
            JWT token string
        """
        import time

        now = datetime.utcnow()
        payload = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "iat": now,
            "exp": now + timedelta(hours=self.token_expiry_hours),
            "jti": f"{user_id}_{int(time.time() * 1000)}",  # Unique token ID
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token

        Args:
            token: JWT token string

        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def refresh_token(self, token: str) -> Optional[str]:
        """
        Refresh an existing token if valid

        Args:
            token: Current JWT token

        Returns:
            New JWT token if current is valid, None otherwise
        """
        payload = self.verify_token(token)
        if payload:
            # Generate new token with same user data
            return self.generate_token(
                user_id=payload.get("user_id"),
                email=payload.get("email"),
                role=payload.get("role", "viewer"),
            )
        return None

    def hash_password(self, password: str) -> str:
        """
        Hash a password using SHA-256

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify a password against its hash

        Args:
            password: Plain text password
            hashed: Hashed password to compare against

        Returns:
            True if password matches hash
        """
        return self.hash_password(password) == hashed

    def extract_bearer_token(self, auth_header: str) -> Optional[str]:
        """
        Extract token from Authorization header

        Args:
            auth_header: Authorization header value (e.g., "Bearer token123")

        Returns:
            Token string if valid format, None otherwise
        """
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        return None


class SessionManager:
    """Manages user sessions and token blacklisting"""

    def __init__(self):
        # In production, use Redis or similar
        self.blacklisted_tokens = set()
        self.active_sessions = {}

    def create_session(self, user_id: str, token: str) -> None:
        """Create a new session for a user"""
        self.active_sessions[user_id] = {
            "token": token,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
        }

    def update_activity(self, user_id: str) -> None:
        """Update last activity time for a user"""
        if user_id in self.active_sessions:
            self.active_sessions[user_id]["last_activity"] = datetime.utcnow()

    def invalidate_token(self, token: str) -> None:
        """Add token to blacklist (for logout)"""
        self.blacklisted_tokens.add(token)

    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        return token in self.blacklisted_tokens

    def cleanup_expired_sessions(self, expiry_hours: int = 24) -> None:
        """Remove expired sessions"""
        cutoff = datetime.utcnow() - timedelta(hours=expiry_hours)
        expired = []

        for user_id, session in self.active_sessions.items():
            if session["last_activity"] < cutoff:
                expired.append(user_id)
                self.blacklisted_tokens.add(session["token"])

        for user_id in expired:
            del self.active_sessions[user_id]
