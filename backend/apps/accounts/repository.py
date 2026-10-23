from core.mongo import get_db
from core.security import hash_password, verify_password
from core.utils import now, to_object_id

ROLES = ("admin", "support_engineer", "user")


def collection():
    return get_db().users


def find_user_by_email(email):
    return collection().find_one({"email": email.lower().strip()})


def find_user_by_id(user_id):
    oid = to_object_id(user_id)
    if not oid:
        return None
    return collection().find_one({"_id": oid})


def create_user(*, name, email, password, role="user", phone=None, user_type=None):
    if role not in ROLES:
        raise ValueError(f"Invalid role '{role}'. Must be one of {ROLES}.")
    if find_user_by_email(email):
        raise ValueError("A user with this email already exists.")

    doc = {
        "name": name,
        "email": email.lower().strip(),
        "phone": phone,
        "password": hash_password(password),
        "role": role,
        "user_type": user_type if role == "user" else None,
        "is_active": True,
        "created_at": now(),
        "updated_at": now(),
    }
    result = collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def verify_credentials(email, password):
    user = find_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["password"]):
        return None
    return user


def list_users(*, role=None, is_active=None, search=None, skip=0, limit=20):
    query = {}
    if role:
        query["role"] = role
    if is_active is not None:
        query["is_active"] = is_active
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]

    total = collection().count_documents(query)
    cursor = collection().find(query).sort("created_at", -1).skip(skip).limit(limit)
    return list(cursor), total


def update_user(user_id, updates):
    oid = to_object_id(user_id)
    if not oid:
        return None
    updates = dict(updates)
    if "password" in updates:
        updates["password"] = hash_password(updates["password"])
    updates["updated_at"] = now()
    collection().update_one({"_id": oid}, {"$set": updates})
    return find_user_by_id(oid)


def deactivate_user(user_id):
    return update_user(user_id, {"is_active": False})


def to_public(doc):
    """Mongo user doc -> plain dict safe to hand back over the API (no password)."""
    data = dict(doc)
    data["id"] = str(data.pop("_id"))
    data.pop("password", None)
    return data
