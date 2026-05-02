"""Admin authentication — JWT issuance and verification.

Bcrypt password verification against ADMIN_PASSWORD_HASH from env.
JWT issuance (HS256, 7-day expiry, signed with JWT_SECRET).
FastAPI dependency `require_admin` that validates JWT from Authorization header.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from raidio.db.settings import Settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

security = HTTPBearer(auto_error=False)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password: The password entered by the user.
        hashed_password: The bcrypt hash from ADMIN_PASSWORD_HASH.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        return _bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        logger.warning("Password verification failed with unexpected error")
        return False


def create_access_token(secret: str, email: str) -> str:
    """Create a JWT access token for the admin user.

    Args:
        secret: JWT_SECRET from settings.
        email: Admin email to embed in the token subject claim.

    Returns:
        Encoded JWT string.
    """
    expire = datetime.now(tz=UTC) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": email,
        "exp": expire,
        "type": "admin",
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str, secret: str) -> str:
    """Decode and validate a JWT access token.

    Args:
        token: The JWT string from the Authorization header.
        secret: JWT_SECRET from settings.

    Returns:
        The admin email from the token subject claim.

    Raises:
        HTTPException: If the token is invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if email is None or token_type != "admin":
            raise credentials_exception
        return email
    except JWTError:
        raise credentials_exception from None


async def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),  # noqa: B008
) -> str:
    """FastAPI dependency that validates the admin JWT.

    Returns the admin email if valid. Raises 401 otherwise.

    Usage::

        @router.get("/admin/stats")
        async def admin_stats(admin_email: str = Depends(require_admin)):
            ...
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = Settings()
    return decode_access_token(credentials.credentials, settings.jwt_secret)
