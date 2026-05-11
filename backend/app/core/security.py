from datetime import datetime, timedelta, timezone
from typing import Any
import base64
import hashlib

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_payload: dict[str, Any] | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra_payload:
        payload.update(extra_payload)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def _token_cipher_key() -> bytes:
    return hashlib.sha256(settings.JWT_SECRET_KEY.encode("utf-8")).digest()


def encrypt_secret(value: str) -> str:
    data = value.encode("utf-8")
    key = _token_cipher_key()
    encrypted = bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data))
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def decrypt_secret(value: str) -> str:
    encrypted = base64.urlsafe_b64decode(value.encode("ascii"))
    key = _token_cipher_key()
    decrypted = bytes(byte ^ key[index % len(key)] for index, byte in enumerate(encrypted))
    return decrypted.decode("utf-8")
