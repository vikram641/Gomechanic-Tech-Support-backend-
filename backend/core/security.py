"""Password hashing compatible with Django's default PBKDF2 hasher.

User docs already stored in Mongo (created by the previous Django+DRF
backend) hold passwords in the format
`pbkdf2_sha256$<iterations>$<salt>$<base64-hash>`, produced by
`django.contrib.auth.hashers.make_password` (PBKDF2PasswordHasher, SHA256,
720000 iterations as of Django 5.0). Reimplemented here without a Django
dependency so existing users don't need to reset their password.
"""

import base64
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 720000
SALT_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
SALT_LENGTH = 12


def _pbkdf2(password: str, salt: str, iterations: int) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    return base64.b64encode(digest).decode("ascii").strip()


def _generate_salt() -> str:
    return "".join(secrets.choice(SALT_CHARS) for _ in range(SALT_LENGTH))


def hash_password(raw_password: str) -> str:
    salt = _generate_salt()
    hashed = _pbkdf2(raw_password, salt, ITERATIONS)
    return f"{ALGORITHM}${ITERATIONS}${salt}${hashed}"


def verify_password(raw_password: str, encoded: str) -> bool:
    if not encoded:
        return False
    try:
        algorithm, iterations, salt, hashed = encoded.split("$", 3)
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    try:
        iterations = int(iterations)
    except ValueError:
        return False
    computed = _pbkdf2(raw_password, salt, iterations)
    return hmac.compare_digest(computed, hashed)
