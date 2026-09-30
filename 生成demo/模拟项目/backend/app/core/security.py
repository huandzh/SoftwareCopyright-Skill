"""会话与口令安全：签发会话 Cookie、校验口令强度。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

from app.core.config import settings

# 口令最少长度与必须包含的字符类别
MIN_PASSWORD_LENGTH = 8
REQUIRED_CLASSES = 2


def hash_password(password: str, *, salt: str | None = None) -> tuple[str, str]:
    """返回 (salt, hash)，使用 PBKDF2-HMAC-SHA256 迭代派生。"""
    actual_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        actual_salt.encode("utf-8"),
        120_000,
    )
    return actual_salt, base64.b64encode(digest).decode("ascii")


def verify_password(password: str, salt: str, expected: str) -> bool:
    _, candidate = hash_password(password, salt=salt)
    # 使用常量时间比较，避免通过响应时间推断口令
    return hmac.compare_digest(candidate, expected)


def password_strength_issues(password: str) -> list[str]:
    """检查口令是否满足平台要求，返回需要提示用户的问题列表。"""
    issues: list[str] = []
    if len(password) < MIN_PASSWORD_LENGTH:
        issues.append(f"密码至少需要 {MIN_PASSWORD_LENGTH} 位。")
    classes = 0
    if any(char.islower() for char in password):
        classes += 1
    if any(char.isupper() for char in password):
        classes += 1
    if any(char.isdigit() for char in password):
        classes += 1
    if any(not char.isalnum() for char in password):
        classes += 1
    if classes < REQUIRED_CLASSES:
        issues.append("密码需要至少包含字母、数字或符号中的两类。")
    return issues


def issue_session_token(user_id: str) -> tuple[str, int]:
    """签发会话令牌，返回令牌与过期时间戳。"""
    expires_at = int(time.time()) + settings.session_ttl_seconds
    payload = f"{user_id}:{expires_at}:{secrets.token_hex(8)}"
    signature = hmac.new(
        settings.database_url.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    token = base64.urlsafe_b64encode(f"{payload}:{signature}".encode("utf-8")).decode("ascii")
    return token, expires_at


def decode_session_token(token: str) -> tuple[str, int] | None:
    """解出用户编号与过期时间；令牌被篡改或过期时返回 None。"""
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        user_id, expires_raw, signature = raw.rsplit(":", 2)
    except (ValueError, UnicodeDecodeError):
        return None
    expires_at = int(expires_raw)
    if expires_at < int(time.time()):
        return None
    expected = hmac.new(
        settings.database_url.encode("utf-8"),
        f"{user_id}:{expires_at}:{raw.split(':')[2]}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    return user_id, expires_at
