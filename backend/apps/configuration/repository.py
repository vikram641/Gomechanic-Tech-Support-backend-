from core.mongo import get_db
from core.utils import now, to_object_id

# Collection names for every dropdown/config type managed from the admin panel.
USER_TYPES = "user_types"
PLATFORMS = "platforms"
TICKET_CATEGORIES = "ticket_categories"
TICKET_PRIORITIES = "ticket_priorities"
WHATSAPP_TEMPLATES = "whatsapp_templates"
SLA_RULES = "sla_rules"

ALL_COLLECTIONS = (
    USER_TYPES,
    PLATFORMS,
    TICKET_CATEGORIES,
    TICKET_PRIORITIES,
    WHATSAPP_TEMPLATES,
    SLA_RULES,
)


def _collection(name):
    if name not in ALL_COLLECTIONS:
        raise ValueError(f"Unknown configuration collection '{name}'.")
    return get_db()[name]


def list_options(collection_name, active_only=False):
    query = {"is_active": True} if active_only else {}
    sort_key = "level" if collection_name == TICKET_PRIORITIES else "name"
    return list(_collection(collection_name).find(query).sort(sort_key, 1))


def get_option(collection_name, option_id):
    oid = to_object_id(option_id)
    if not oid:
        return None
    return _collection(collection_name).find_one({"_id": oid})


def get_option_by_name(collection_name, name):
    return _collection(collection_name).find_one({"name": name})


def is_active_option(collection_name, name):
    doc = get_option_by_name(collection_name, name)
    return bool(doc and doc.get("is_active", True))


def is_active_template_key(key):
    doc = _collection(WHATSAPP_TEMPLATES).find_one({"key": key})
    return bool(doc and doc.get("is_active", True))


def get_template_by_key(key):
    return _collection(WHATSAPP_TEMPLATES).find_one({"key": key})


_LOOKUP_FIELD_BY_COLLECTION = {
    WHATSAPP_TEMPLATES: "key",
    SLA_RULES: "priority",
}


def create_option(collection_name, data):
    lookup_field = _LOOKUP_FIELD_BY_COLLECTION.get(collection_name, "name")
    if _collection(collection_name).find_one({lookup_field: data[lookup_field]}):
        raise ValueError(f"'{data[lookup_field]}' already exists in {collection_name}.")

    doc = {**data, "is_active": data.get("is_active", True), "created_at": now(), "updated_at": now()}
    result = _collection(collection_name).insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def update_option(collection_name, option_id, data):
    oid = to_object_id(option_id)
    if not oid:
        return None
    updates = {**data, "updated_at": now()}
    _collection(collection_name).update_one({"_id": oid}, {"$set": updates})
    return get_option(collection_name, oid)


def delete_option(collection_name, option_id):
    """Soft delete — tickets may still reference this value historically."""
    return update_option(collection_name, option_id, {"is_active": False})


def get_sla_rule_for_priority(priority_name):
    return _collection(SLA_RULES).find_one({"priority": priority_name})


def to_public(doc):
    if doc is None:
        return None
    data = dict(doc)
    data["id"] = str(data.pop("_id"))
    return data
