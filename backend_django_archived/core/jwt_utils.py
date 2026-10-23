from datetime import timedelta

import jwt
from django.conf import settings

from core.utils import now


class TokenError(Exception):
    pass


def _encode(sub, role, token_type, ttl):
    payload = {
        "sub": sub,
        "role": role,
        "type": token_type,
        "iat": now(),
        "exp": now() + ttl,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_doc):
    return _encode(
        str(user_doc["_id"]),
        user_doc.get("role"),
        "access",
        timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES),
    )


def create_refresh_token(user_doc):
    return _encode(
        str(user_doc["_id"]),
        user_doc.get("role"),
        "refresh",
        timedelta(days=settings.JWT_REFRESH_TTL_DAYS),
    )


def create_token_pair(user_doc):
    return {
        "access": create_access_token(user_doc),
        "refresh": create_refresh_token(user_doc),
    }


def decode_token(token, expected_type):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Token is invalid") from exc

    if payload.get("type") != expected_type:
        raise TokenError(f"Expected a {expected_type} token")
    return payload
