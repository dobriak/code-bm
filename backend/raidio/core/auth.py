from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from raidio.db.settings import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


class TokenPayload(BaseModel):
    sub: str
    exp: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(email: str, secret: str | None = None) -> str:
    settings = get_settings()
    key = secret or settings.jwt_secret
    exp = datetime.now(UTC) + timedelta(days=7)
    payload = TokenPayload(sub=email, exp=exp)
    return jwt.encode(payload.model_dump(), key, algorithm="HS256")


def decode_token(token: str, secret: str | None = None) -> TokenPayload:
    settings = get_settings()
    key = secret or settings.jwt_secret
    return TokenPayload(**jwt.decode(token, key, algorithms=["HS256"]))


async def require_admin(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    settings = get_settings()
    if not settings.admin_email:
        raise HTTPException(status_code=500, detail="Admin not configured")

    token = credentials.credentials
    try:
        payload = decode_token(token, settings.jwt_secret)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.sub != settings.admin_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return payload.sub


async def authenticate_admin(email: str, password: str) -> str | None:
    settings = get_settings()
    if email != settings.admin_email:
        return None
    if not verify_password(password, settings.admin_password_hash):
        return None
    return create_access_token(email, settings.jwt_secret)
