from typing import Annotated

from fastapi import Depends, Header, HTTPException

from core.jwt_utils import TokenError, decode_token
from core.utils import to_object_id

ADMIN = "admin"
SUPPORT_ENGINEER = "support_engineer"
USER = "user"
STAFF_ROLES = (ADMIN, SUPPORT_ENGINEER)


class MongoUser:
    """Lightweight stand-in for Django's User, backed by a Mongo user document."""

    def __init__(self, doc):
        self._doc = doc
        self.id = str(doc["_id"])
        self.email = doc.get("email")
        self.name = doc.get("name")
        self.phone = doc.get("phone")
        self.role = doc.get("role")
        self.user_type = doc.get("user_type")
        self.is_active = doc.get("is_active", True)
        self.is_authenticated = True

    def __getitem__(self, key):
        return self._doc[key]


def get_current_user_optional(
    authorization: Annotated[str | None, Header()] = None,
) -> MongoUser | None:
    """Decode the bearer token if present and valid; return None on ANY
    failure (missing header, malformed, expired/invalid/wrong-type token,
    user not found, inactive user) rather than raising.

    A bad/expired token on the request must NOT hard-fail a public route —
    mirrors the previous DRF JWTAuthentication behavior so a stale token
    left in localStorage doesn't 401 pages like /raise-ticket or
    registration that don't require auth at all. Routes that DO require
    auth depend on `get_current_user` below, which raises on None.
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError:
        return None

    # Imported lazily to avoid a circular import (accounts.router imports
    # this module too).
    from apps.accounts.repository import find_user_by_id

    user_id = to_object_id(payload.get("sub"))
    user_doc = find_user_by_id(user_id) if user_id else None
    if not user_doc or not user_doc.get("is_active", True):
        return None

    return MongoUser(user_doc)


def get_current_user(
    user: Annotated[MongoUser | None, Depends(get_current_user_optional)],
) -> MongoUser:
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication credentials were not provided.")
    return user


def require_role(*roles: str):
    def _dependency(user: Annotated[MongoUser, Depends(get_current_user)]) -> MongoUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action.")
        return user

    return _dependency


require_admin = require_role(ADMIN)
require_support_staff = require_role(ADMIN, SUPPORT_ENGINEER)
