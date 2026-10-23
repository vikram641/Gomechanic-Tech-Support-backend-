from types import SimpleNamespace

from apps.tickets import constants
from core.mongo import get_db
from core.utils import generate_ticket_id, now, to_object_id


def collection():
    return get_db().tickets


def _log_activity(ticket_oid, *, actor, action, from_status=None, to_status=None, note=None):
    actor_id = getattr(actor, "id", None) if actor else None
    entry = {
        "actor_id": str(actor_id) if actor_id else None,
        "actor_name": getattr(actor, "name", None) if actor else None,
        "action": action,
        "from_status": from_status,
        "to_status": to_status,
        "note": note,
        "created_at": now(),
    }
    collection().update_one(
        {"_id": ticket_oid},
        {"$push": {"activity_log": entry}, "$set": {"updated_at": now()}},
    )
    return entry


def create_ticket(*, title, description, user_type, platform, category=None,
                   priority=None, login_credentials=None, attachments=None,
                   creator=None, guest_name=None, guest_email=None, guest_phone=None):
    """Create a ticket either on behalf of a logged-in account (`creator`) or
    a guest with no account (`guest_name`/`guest_email`/`guest_phone`), for
    the no-login public submission form. Exactly one of the two must be
    supplied — enforced by the two callers in router.py, not here.
    """
    if creator:
        created_by = creator.id
        snapshot = {"name": creator.name, "email": creator.email, "phone": creator.phone}
    else:
        created_by = None
        snapshot = {"name": guest_name, "email": guest_email, "phone": guest_phone}

    doc = {
        "ticket_id": generate_ticket_id(),
        "title": title,
        "description": description,
        "user_type": user_type,
        "platform": platform,
        "category": category,
        "priority": priority or constants.DEFAULT_PRIORITY,
        "status": constants.OPEN,
        "login_credentials": login_credentials,
        "attachments": attachments or [],
        "created_by": created_by,
        "created_by_snapshot": snapshot,
        "assigned_to": None,
        "assigned_to_snapshot": None,
        "internal_notes": [],
        "activity_log": [],
        "csat_status": None,
        "reopened_count": 0,
        "first_response_at": None,
        "resolved_at": None,
        "closed_at": None,
        "created_at": now(),
        "updated_at": now(),
    }
    result = collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    activity_actor = creator or SimpleNamespace(id=None, name=guest_name)
    _log_activity(doc["_id"], actor=activity_actor, action="ticket_created", to_status=constants.OPEN)
    return get_ticket(doc["_id"])


def get_ticket(ticket_id):
    """Look up by Mongo _id or by the human-readable ticket_id (e.g. GM-2001)."""
    oid = to_object_id(ticket_id)
    if oid:
        doc = collection().find_one({"_id": oid})
        if doc:
            return doc
    return collection().find_one({"ticket_id": ticket_id})


def list_tickets(*, status=None, user_type=None, platform=None, priority=None,
                  assigned_to=None, created_by=None, date_from=None, date_to=None,
                  search=None, skip=0, limit=20):
    query = {}
    if status:
        query["status"] = status
    if user_type:
        query["user_type"] = user_type
    if platform:
        query["platform"] = platform
    if priority:
        query["priority"] = priority
    if assigned_to:
        query["assigned_to"] = assigned_to
    if created_by:
        query["created_by"] = created_by
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        query["created_at"] = date_query
    if search:
        query["$or"] = [
            {"ticket_id": {"$regex": search, "$options": "i"}},
            {"title": {"$regex": search, "$options": "i"}},
            {"created_by_snapshot.name": {"$regex": search, "$options": "i"}},
            {"created_by_snapshot.email": {"$regex": search, "$options": "i"}},
        ]

    total = collection().count_documents(query)
    cursor = collection().find(query).sort("created_at", -1).skip(skip).limit(limit)
    return list(cursor), total


def assign_ticket(ticket_oid, *, engineer, actor):
    ticket = get_ticket(ticket_oid)
    if not ticket:
        return None
    prev_status = ticket["status"]
    new_status = constants.ASSIGNED if prev_status == constants.OPEN else prev_status
    collection().update_one(
        {"_id": ticket["_id"]},
        {
            "$set": {
                "assigned_to": engineer.id,
                "assigned_to_snapshot": {"name": engineer.name, "email": engineer.email},
                "status": new_status,
                "updated_at": now(),
            }
        },
    )
    _log_activity(
        ticket["_id"],
        actor=actor,
        action="assigned",
        from_status=prev_status,
        to_status=new_status,
        note=f"Assigned to {engineer.name}",
    )
    return get_ticket(ticket["_id"])


def update_status(ticket_oid, *, new_status, actor, note=None):
    ticket = get_ticket(ticket_oid)
    if not ticket:
        return None, "Ticket not found."

    current = ticket["status"]
    if new_status not in constants.ALL_STATUSES:
        return None, f"'{new_status}' is not a valid status."
    if new_status == current:
        return None, "Ticket is already in this status."
    if new_status not in constants.ALLOWED_TRANSITIONS.get(current, set()):
        return None, f"Cannot move a ticket from '{current}' to '{new_status}'."

    updates = {"status": new_status, "updated_at": now()}
    if new_status == constants.IN_PROGRESS and not ticket.get("first_response_at"):
        updates["first_response_at"] = now()
    if new_status == constants.RESOLVED:
        updates["resolved_at"] = now()
        updates["csat_status"] = "pending"
    if new_status == constants.CLOSED:
        updates["closed_at"] = now()
    if new_status == constants.REOPENED:
        updates["reopened_count"] = ticket.get("reopened_count", 0) + 1
        updates["resolved_at"] = None
        updates["closed_at"] = None
        # csat_status is left as-is here (record_csat_response sets it to
        # "not_satisfied" just before this transition) so analytics can still
        # see why the ticket reopened; the next Resolved sets it to "pending".

    collection().update_one({"_id": ticket["_id"]}, {"$set": updates})
    _log_activity(
        ticket["_id"], actor=actor, action="status_changed",
        from_status=current, to_status=new_status, note=note,
    )
    return get_ticket(ticket["_id"]), None


def record_csat_response(ticket_oid, *, satisfied, actor=None):
    ticket = get_ticket(ticket_oid)
    if not ticket:
        return None, "Ticket not found."
    if ticket["status"] != constants.RESOLVED:
        return None, "CSAT response can only be recorded for a Resolved ticket."

    collection().update_one(
        {"_id": ticket["_id"]},
        {"$set": {"csat_status": "satisfied" if satisfied else "not_satisfied", "updated_at": now()}},
    )

    if satisfied:
        return update_status(ticket_oid, new_status=constants.CLOSED, actor=actor,
                              note="User confirmed satisfaction via WhatsApp.")
    return update_status(ticket_oid, new_status=constants.REOPENED, actor=actor,
                          note="User was not satisfied via WhatsApp; reopened for rework.")


def add_note(ticket_oid, *, actor, note):
    ticket = get_ticket(ticket_oid)
    if not ticket:
        return None
    entry = {
        "author_id": str(actor.id),
        "author_name": actor.name,
        "note": note,
        "created_at": now(),
    }
    collection().update_one(
        {"_id": ticket["_id"]},
        {"$push": {"internal_notes": entry}, "$set": {"updated_at": now()}},
    )
    _log_activity(ticket["_id"], actor=actor, action="note_added")
    return get_ticket(ticket["_id"])


def add_attachment(ticket_oid, attachment):
    collection().update_one(
        {"_id": to_object_id(ticket_oid)},
        {"$push": {"attachments": attachment}, "$set": {"updated_at": now()}},
    )
    return get_ticket(ticket_oid)


def to_public(doc):
    if doc is None:
        return None
    data = dict(doc)
    data["id"] = str(data.pop("_id"))
    data["created_by"] = str(data["created_by"]) if data.get("created_by") else None
    data["assigned_to"] = str(data["assigned_to"]) if data.get("assigned_to") else None
    return data
