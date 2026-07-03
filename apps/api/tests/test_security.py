"""Unit tests for JWT issuing/verification (no DB required)."""
from app.core.security import create_access_token, decode_token


def test_jwt_roundtrip():
    token = create_access_token("user-123", "admin")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"


def test_invalid_jwt_returns_none():
    assert decode_token("not-a-real-token") is None
