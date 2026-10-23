from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from core.mongo import get_db


def now():
    return datetime.now(timezone.utc)


def to_object_id(value):
    """Return an ObjectId for value, or None if value isn't a valid ObjectId."""
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        return None


def oid_str(value):
    """Stringify an ObjectId (or return value unchanged if it isn't one)."""
    return str(value) if isinstance(value, ObjectId) else value


def serialize_doc(doc):
    """Recursively convert ObjectId/datetime fields on a Mongo document into
    JSON-friendly str values, and rename _id -> id."""
    if doc is None:
        return None
    result = {}
    for key, value in doc.items():
        out_key = "id" if key == "_id" else key
        result[out_key] = _serialize_value(value)
    return result


def _serialize_value(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {("id" if k == "_id" else k): _serialize_value(v) for k, v in value.items()}
    return value


def next_sequence(name):
    """Atomically increment and return the next value of a named counter,
    stored in the `counters` collection. Used for human-readable ticket IDs."""
    result = get_db().counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return result["seq"]


def generate_ticket_id():
    seq = next_sequence("ticket_id")
    return f"GM-{2000 + seq}"
