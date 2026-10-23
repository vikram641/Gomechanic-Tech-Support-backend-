from apps.configuration.repository import get_sla_rule_for_priority
from apps.tickets import constants
from apps.tickets.repository import collection as tickets_collection


def _date_match(date_from=None, date_to=None):
    if not date_from and not date_to:
        return {}
    date_query = {}
    if date_from:
        date_query["$gte"] = date_from
    if date_to:
        date_query["$lte"] = date_to
    return {"created_at": date_query}


def _group_count(field, date_from=None, date_to=None):
    pipeline = []
    match = _date_match(date_from, date_to)
    if match:
        pipeline.append({"$match": match})
    pipeline.append({"$group": {"_id": f"${field}", "count": {"$sum": 1}}})
    return {(doc["_id"] or "Unknown"): doc["count"] for doc in tickets_collection().aggregate(pipeline)}


def tickets_by_status(date_from=None, date_to=None):
    return _group_count("status", date_from, date_to)


def tickets_by_platform(date_from=None, date_to=None):
    return _group_count("platform", date_from, date_to)


def tickets_by_user_type(date_from=None, date_to=None):
    return _group_count("user_type", date_from, date_to)


def resolved_per_engineer(date_from=None, date_to=None):
    match = _date_match(date_from, date_to)
    match["status"] = {"$in": [constants.RESOLVED, constants.CLOSED]}
    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$assigned_to_snapshot.name", "resolved_count": {"$sum": 1}}},
        {"$sort": {"resolved_count": -1}},
    ]
    return [
        {"engineer": doc["_id"] or "Unassigned", "resolved_count": doc["resolved_count"]}
        for doc in tickets_collection().aggregate(pipeline)
    ]


def period_trend(period, date_from=None, date_to=None):
    """period: 'day' | 'week' | 'month' — ticket-count trend for charts."""
    date_format = {"day": "%Y-%m-%d", "week": "%G-W%V", "month": "%Y-%m"}[period]
    pipeline = []
    match = _date_match(date_from, date_to)
    if match:
        pipeline.append({"$match": match})
    pipeline.append(
        {
            "$group": {
                "_id": {"$dateToString": {"format": date_format, "date": "$created_at"}},
                "count": {"$sum": 1},
            }
        }
    )
    pipeline.append({"$sort": {"_id": 1}})
    return [
        {"period": doc["_id"], "count": doc["count"]}
        for doc in tickets_collection().aggregate(pipeline)
    ]


def avg_duration_hours(timestamp_field, date_from=None, date_to=None):
    match = _date_match(date_from, date_to)
    match[timestamp_field] = {"$ne": None}
    docs = tickets_collection().find(match, {"created_at": 1, timestamp_field: 1})
    diffs = [
        (doc[timestamp_field] - doc["created_at"]).total_seconds()
        for doc in docs
        if doc.get(timestamp_field)
    ]
    if not diffs:
        return 0.0
    return round((sum(diffs) / len(diffs)) / 3600, 2)


def avg_first_response_minutes(date_from=None, date_to=None):
    match = _date_match(date_from, date_to)
    match["first_response_at"] = {"$ne": None}
    docs = tickets_collection().find(match, {"created_at": 1, "first_response_at": 1})
    diffs = [(doc["first_response_at"] - doc["created_at"]).total_seconds() for doc in docs]
    if not diffs:
        return 0.0
    return round((sum(diffs) / len(diffs)) / 60, 2)


def reopened_tickets_count(date_from=None, date_to=None):
    match = _date_match(date_from, date_to)
    match["reopened_count"] = {"$gt": 0}
    return tickets_collection().count_documents(match)


def pending_tickets_count(date_from=None, date_to=None):
    match = _date_match(date_from, date_to)
    match["status"] = {"$nin": [constants.CLOSED]}
    return tickets_collection().count_documents(match)


def csat_summary(date_from=None, date_to=None):
    match = _date_match(date_from, date_to)
    match["csat_status"] = {"$in": ["satisfied", "not_satisfied"]}
    satisfied = tickets_collection().count_documents({**match, "csat_status": "satisfied"})
    not_satisfied = tickets_collection().count_documents({**match, "csat_status": "not_satisfied"})
    total = satisfied + not_satisfied
    percentage = round((satisfied / total) * 100, 1) if total else 0.0
    return {"satisfied": satisfied, "not_satisfied": not_satisfied, "csat_percentage": percentage}


def sla_compliance(date_from=None, date_to=None):
    match = _date_match(date_from, date_to)
    match["resolved_at"] = {"$ne": None}
    docs = list(tickets_collection().find(match, {"priority": 1, "created_at": 1, "resolved_at": 1}))
    if not docs:
        return {"compliant": 0, "total": 0, "sla_percentage": 0.0}

    compliant = 0
    rule_cache = {}
    for doc in docs:
        priority = doc.get("priority")
        if priority not in rule_cache:
            rule_cache[priority] = get_sla_rule_for_priority(priority)
        rule = rule_cache[priority]
        if not rule:
            continue
        minutes_taken = (doc["resolved_at"] - doc["created_at"]).total_seconds() / 60
        if minutes_taken <= rule["resolution_time_minutes"]:
            compliant += 1

    total = len(docs)
    return {
        "compliant": compliant,
        "total": total,
        "sla_percentage": round((compliant / total) * 100, 1) if total else 0.0,
    }


def build_summary(date_from=None, date_to=None):
    return {
        "total_tickets": tickets_collection().count_documents(_date_match(date_from, date_to)),
        "tickets_by_status": tickets_by_status(date_from, date_to),
        "tickets_by_platform": tickets_by_platform(date_from, date_to),
        "tickets_by_user_type": tickets_by_user_type(date_from, date_to),
        "resolved_per_engineer": resolved_per_engineer(date_from, date_to),
        "avg_resolution_time_hours": avg_duration_hours("resolved_at", date_from, date_to),
        "avg_first_response_time_minutes": avg_first_response_minutes(date_from, date_to),
        "reopened_tickets": reopened_tickets_count(date_from, date_to),
        "pending_tickets": pending_tickets_count(date_from, date_to),
        "csat": csat_summary(date_from, date_to),
        "sla_compliance": sla_compliance(date_from, date_to),
        "daily_trend": period_trend("day", date_from, date_to),
        "weekly_trend": period_trend("week", date_from, date_to),
        "monthly_trend": period_trend("month", date_from, date_to),
    }
