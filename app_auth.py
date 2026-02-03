from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from typing import Any, Dict, Optional, Tuple


def _pbkdf2_hash(password: str, salt: bytes, rounds: int = 120_000) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)


def hash_password(password: str, salt_b64: Optional[str] = None) -> Tuple[str, str]:
    if salt_b64 is None:
        salt = os.urandom(16)
    else:
        salt = base64.b64decode(salt_b64.encode("utf-8"))
    digest = _pbkdf2_hash(password, salt)
    return base64.b64encode(salt).decode("utf-8"), base64.b64encode(digest).decode("utf-8")


def load_users(path: str = "users.json") -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"users": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "users" not in data or not isinstance(data["users"], dict):
            return {"users": {}}
        return data
    except Exception:
        return {"users": {}}


def save_users(data: Dict[str, Any], path: str = "users.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def verify_user(users_data: Dict[str, Any], username: str, password: str) -> bool:
    user = users_data.get("users", {}).get(username)
    if not user:
        return False
    salt_b64 = user.get("salt")
    hash_b64 = user.get("hash")
    if not salt_b64 or not hash_b64:
        return False
    _, computed_hash = hash_password(password, salt_b64=salt_b64)
    return _constant_time_equals(computed_hash, hash_b64)


def get_user_role(users_data: Dict[str, Any], username: str) -> str:
    user = users_data.get("users", {}).get(username, {})
    role = user.get("role", "user")
    return role if role in ("admin", "user") else "user"


def is_valid_username(username: str) -> bool:
    return bool(re.fullmatch(r"[a-zA-Z0-9_\\-]{3,32}", username))


def create_user(users_data: Dict[str, Any], username: str, password: str, role: str = "user") -> Tuple[bool, str]:
    username = username.strip()
    if not is_valid_username(username):
        return False, "Kullanıcı adı 3-32 karakter olmalı (harf, rakam, _ veya -)."
    if username in users_data.get("users", {}):
        return False, "Bu kullanıcı adı zaten var."
    if len(password) < 6:
        return False, "Şifre en az 6 karakter olmalı."
    role = "admin" if role == "admin" else "user"
    salt_b64, hash_b64 = hash_password(password)
    users_data.setdefault("users", {})[username] = {
        "salt": salt_b64,
        "hash": hash_b64,
        "role": role,
    }
    return True, "Kullanıcı oluşturuldu."


def update_password(users_data: Dict[str, Any], username: str, new_password: str) -> Tuple[bool, str]:
    if username not in users_data.get("users", {}):
        return False, "Kullanıcı bulunamadı."
    if len(new_password) < 6:
        return False, "Şifre en az 6 karakter olmalı."
    salt_b64, hash_b64 = hash_password(new_password)
    users_data["users"][username]["salt"] = salt_b64
    users_data["users"][username]["hash"] = hash_b64
    return True, "Şifre güncellendi."


def delete_user(users_data: Dict[str, Any], username: str) -> Tuple[bool, str]:
    if username not in users_data.get("users", {}):
        return False, "Kullanıcı bulunamadı."
    users_data["users"].pop(username, None)
    return True, "Kullanıcı silindi."


def _constant_time_equals(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a.encode("utf-8"), b.encode("utf-8")):
        result |= x ^ y
    return result == 0
