"""Unit tests for admin authentication — JWT issuance/verification, password hashing."""

from __future__ import annotations

import time

import pytest

from raidio.core.auth import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
    verify_password,
)


class TestPasswordVerification:
    """Tests for bcrypt password verification."""

    def test_verify_correct_password(self):
        """Returns True for a matching password."""
        # Generate a hash fresh to avoid stale hashes
        import bcrypt as _bcrypt

        hashed = _bcrypt.hashpw(b"password123", _bcrypt.gensalt(rounds=12)).decode()
        assert verify_password("password123", hashed) is True

    def test_verify_wrong_password(self):
        """Returns False for a non-matching password."""
        import bcrypt as _bcrypt

        hashed = _bcrypt.hashpw(b"password123", _bcrypt.gensalt(rounds=12)).decode()
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_empty_password(self):
        """Returns False for empty password."""
        import bcrypt as _bcrypt

        hashed = _bcrypt.hashpw(b"password123", _bcrypt.gensalt(rounds=12)).decode()
        assert verify_password("", hashed) is False

    def test_verify_invalid_hash(self):
        """Returns False for a malformed hash."""
        assert verify_password("password", "not-a-bcrypt-hash") is False


class TestJwtIssuanceAndVerification:
    """Tests for JWT token creation and validation."""

    SECRET = "test-secret-key-for-jwt"

    def test_create_token_returns_string(self):
        """create_access_token returns a non-empty string."""
        token = create_access_token(self.SECRET, "admin@raidio.local")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self):
        """decode_access_token returns the email from a valid token."""
        token = create_access_token(self.SECRET, "admin@raidio.local")
        email = decode_access_token(token, self.SECRET)
        assert email == "admin@raidio.local"

    def test_decode_wrong_secret_raises(self):
        """decode_access_token raises HTTPException for wrong secret."""
        from fastapi import HTTPException

        token = create_access_token(self.SECRET, "admin@raidio.local")
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token, "wrong-secret")
        assert exc_info.value.status_code == 401

    def test_decode_expired_token_raises(self):
        """decode_access_token raises HTTPException for expired token."""
        # Create an already-expired token
        from datetime import UTC, datetime, timedelta

        from fastapi import HTTPException
        from jose import jwt

        expire = datetime.now(tz=UTC) - timedelta(hours=1)
        payload = {
            "sub": "admin@raidio.local",
            "exp": expire,
            "type": "admin",
        }
        expired_token = jwt.encode(payload, self.SECRET, algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(expired_token, self.SECRET)
        assert exc_info.value.status_code == 401

    def test_decode_non_admin_type_raises(self):
        """decode_access_token raises HTTPException if token type is not 'admin'."""
        from fastapi import HTTPException
        from jose import jwt

        payload = {
            "sub": "admin@raidio.local",
            "exp": int(time.time()) + 3600,
            "type": "user",
        }
        token = jwt.encode(payload, self.SECRET, algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token, self.SECRET)
        assert exc_info.value.status_code == 401

    def test_decode_missing_sub_raises(self):
        """decode_access_token raises HTTPException if 'sub' claim is missing."""
        from fastapi import HTTPException
        from jose import jwt

        payload = {
            "exp": int(time.time()) + 3600,
            "type": "admin",
        }
        token = jwt.encode(payload, self.SECRET, algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token, self.SECRET)
        assert exc_info.value.status_code == 401

    def test_decode_malformed_token_raises(self):
        """decode_access_token raises HTTPException for garbage string."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("not-a-jwt-token", self.SECRET)
        assert exc_info.value.status_code == 401
