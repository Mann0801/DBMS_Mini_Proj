"""Accounts: password hashing, login tokens, sign-up. Owner: Mann.

Passwords are never stored. We store
    pbkdf2_sha256$<iterations>$<salt>$<hash>
made with Python's built-in hashlib (200,000 rounds of SHA-256).

After login the user gets a signed token:
    <payload>.<signature>
payload = base64 of {"uid": 3, "exp": <unix time>}
signature = HMAC-SHA256 of the payload with SECRET_KEY from .env.
Nobody can change the payload without the signature breaking. The
user's role is always read fresh from the database, not from the token.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import HTTPException

ITERATIONS = 200_000
TOKEN_HOURS = 12


# ---------------------------------------------------------------- passwords

def hash_password(password: str) -> str:
    salt = secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, expected = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
        return hmac.compare_digest(base64.b64encode(digest).decode(), expected)
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------- tokens

def _secret() -> bytes:
    key = os.getenv("SECRET_KEY", "")
    if len(key) < 16:
        raise HTTPException(500, "SECRET_KEY in .env is missing or too short")
    return key.encode()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_token(user_id: int) -> str:
    payload = _b64(json.dumps({"uid": user_id, "exp": int(time.time()) + TOKEN_HOURS * 3600}).encode())
    signature = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def read_token(token: str) -> int | None:
    """Return the user id if the token is genuine and not expired."""
    try:
        payload, signature = token.split(".")
        expected = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(_unb64(payload))
        if data["exp"] < time.time():
            return None
        return int(data["uid"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------- users

PUBLIC_COLUMNS = "user_id, name, email, role, phone, is_active, created_at"


def _public(user):
    user = dict(user)
    user.pop("password_hash", None)
    user["is_active"] = bool(user["is_active"])
    return user


def get_user(conn, user_id):
    with conn.cursor() as cur:
        cur.execute(f"SELECT {PUBLIC_COLUMNS} FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
    return _public(row) if row else None


def login(conn, email, password):
    with conn.cursor() as cur:
        cur.execute(f"SELECT {PUBLIC_COLUMNS}, password_hash FROM users WHERE email = %s",
                    (email.strip().lower(),))
        user = cur.fetchone()
    # same message whether the email or the password is wrong
    if user is None or not verify_password(password, user["password_hash"]):
        raise HTTPException(401, "Wrong email or password")
    if not user["is_active"]:
        raise HTTPException(403, "This account is disabled")
    return {"token": make_token(user["user_id"]), "user": _public(user)}


def create_user(conn, name, email, password, phone, role="student"):
    # a duplicate email raises IntegrityError 1062 -> clean 409 in main.py
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (name, email, password_hash, role, phone) "
            "VALUES (%s, %s, %s, %s, %s)",
            (name.strip(), email.strip().lower(), hash_password(password), role, phone),
        )
        user_id = cur.lastrowid
    return get_user(conn, user_id)


def list_users(conn, role=None):
    with conn.cursor() as cur:
        if role:
            cur.execute(f"SELECT {PUBLIC_COLUMNS} FROM users WHERE role = %s ORDER BY name", (role,))
        else:
            cur.execute(f"SELECT {PUBLIC_COLUMNS} FROM users ORDER BY role, name")
        return [_public(r) for r in cur.fetchall()]


def set_active(conn, user_id, active, acting_user_id):
    if user_id == acting_user_id and not active:
        raise HTTPException(409, "You cannot disable your own account")
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET is_active = %s WHERE user_id = %s", (active, user_id))
        if cur.rowcount == 0 and get_user(conn, user_id) is None:
            raise HTTPException(404, "User not found")
    return get_user(conn, user_id)
