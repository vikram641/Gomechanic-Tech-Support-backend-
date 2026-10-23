from core.mongo import get_db
from core.pagination import get_skip_limit
from core.utils import now


def collection():
    return get_db().notification_logs


def log_notification(*, ticket_id, template_key, to_phone, payload, status,
                      karix_message_id=None, error=None):
    doc = {
        "ticket_id": ticket_id,
        "template_key": template_key,
        "to_phone": to_phone,
        "payload": payload,
        "status": status,
        "karix_message_id": karix_message_id,
        "error": error,
        "created_at": now(),
    }
    result = collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def list_logs(*, ticket_id=None, status=None, request=None):
    query = {}
    if ticket_id:
        query["ticket_id"] = ticket_id
    if status:
        query["status"] = status

    total = collection().count_documents(query)
    skip, limit, page = get_skip_limit(request) if request else (0, 20, 1)
    cursor = collection().find(query).sort("created_at", -1).skip(skip).limit(limit)
    return list(cursor), total, page, limit


def to_public(doc):
    if doc is None:
        return None
    data = dict(doc)
    data["id"] = str(data.pop("_id"))
    return data
