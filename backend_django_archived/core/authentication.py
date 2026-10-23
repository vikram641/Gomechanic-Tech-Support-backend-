from rest_framework import authentication

from core.jwt_utils import TokenError, decode_token
from core.utils import to_object_id


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


class JWTAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode("utf-8", "ignore")
        if not header:
            return None

        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != self.keyword.lower():
            return None

        token = parts[1]
        try:
            payload = decode_token(token, expected_type="access")
        except TokenError:
            # A bad/expired token on the request must NOT hard-fail a public
            # (AllowAny) endpoint — DRF runs authentication before the
            # permission check, so raising here would 401 pages like
            # /raise-ticket or the registration form just because the
            # browser still has a stale token from an earlier logged-in
            # session. Treat it as "no credentials" instead; anything that
            # actually requires auth is still enforced by IsAuthenticated /
            # IsAdmin / IsSupportStaff on the view.
            return None

        # Imported lazily to avoid a circular import at app-loading time.
        from apps.accounts.repository import find_user_by_id

        user_id = to_object_id(payload.get("sub"))
        user_doc = find_user_by_id(user_id) if user_id else None
        if not user_doc or not user_doc.get("is_active", True):
            return None

        return (MongoUser(user_doc), token)

    def authenticate_header(self, request):
        return self.keyword
