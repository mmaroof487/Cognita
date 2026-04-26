"""
Security module — JWT, OAuth, encryption helpers.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from jose import JWTError
from fastapi import HTTPException, status
from cryptography.fernet import Fernet, InvalidToken
from app.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# Encryption (Fernet)
# ─────────────────────────────────────────────────────────────────────────────

def encrypt_token(token: str) -> str:
    """Encrypt a token using Fernet."""
    cipher = Fernet(settings.encryption_key.encode())
    return cipher.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt a token using Fernet."""
    try:
        cipher = Fernet(settings.encryption_key.encode())
        return cipher.decrypt(encrypted.encode()).decode()
    except InvalidToken:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid encrypted token"
        )


# ─────────────────────────────────────────────────────────────────────────────
# JWT Tokens
# ─────────────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm="HS256"
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm="HS256"
    )
    return encoded_jwt


def verify_token(token: str, expected_type: str = "access") -> dict:
    """Verify a JWT token and return payload."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"]
        )
        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {expected_type}"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


# ─────────────────────────────────────────────────────────────────────────────
# OAuth Helpers
# ─────────────────────────────────────────────────────────────────────────────

def create_oauth_state_token() -> str:
    """Create a random state token for OAuth flow."""
    import secrets
    return secrets.token_urlsafe(32)


def verify_oauth_state(state: str, stored_state: str) -> bool:
    """Verify OAuth state token matches stored value."""
    return state == stored_state
