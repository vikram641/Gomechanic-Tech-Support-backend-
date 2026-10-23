from apps.configuration import repository

DEFAULT_USER_TYPES = [
    "CR",
    "Central CR",
    "Lead Call Center",
    "Chat Support",
    "Garage Owner",
    "Service Adviser",
]

DEFAULT_PLATFORMS = [
    "CR App",
    "Master Lead Dashboard",
    "Garage Dashboard",
    "CRM Portal",
    "Workshop Portal",
    "Other Internal Applications",
]

DEFAULT_TICKET_CATEGORIES = [
    "Login / Access Issue",
    "Application Bug",
    "Data Sync Issue",
    "Performance Issue",
    "Feature Request",
    "Other",
]

DEFAULT_PRIORITIES = [
    {"name": "Low", "level": 4},
    {"name": "Medium", "level": 3},
    {"name": "High", "level": 2},
    {"name": "Urgent", "level": 1},
]

# key -> description; karix_template_id left blank until real templates are shared.
DEFAULT_WHATSAPP_TEMPLATES = {
    "TICKET_CREATED": "Sent when a user raises a new ticket.",
    "TICKET_ASSIGNED": "Sent when a ticket is assigned to a support engineer.",
    "TICKET_IN_PROGRESS": "Sent when an engineer starts investigating.",
    "INFO_REQUIRED": "Sent when the engineer needs more information from the user.",
    "TICKET_RESOLVED": "Sent when a ticket is marked Resolved.",
    "CSAT_CHECK": "Follow-up asking if the user is satisfied with the resolution.",
    "TICKET_REOPENED": "Sent when a ticket is reopened after a 'not satisfied' response.",
    "TICKET_CLOSED": "Sent when a ticket is closed after a 'satisfied' response.",
}

DEFAULT_SLA_RULES = [
    {"priority": "Urgent", "response_time_minutes": 15, "resolution_time_minutes": 240},
    {"priority": "High", "response_time_minutes": 30, "resolution_time_minutes": 480},
    {"priority": "Medium", "response_time_minutes": 60, "resolution_time_minutes": 1440},
    {"priority": "Low", "response_time_minutes": 240, "resolution_time_minutes": 4320},
]


def seed_defaults():
    created = []

    for name in DEFAULT_USER_TYPES:
        if not repository.get_option_by_name(repository.USER_TYPES, name):
            repository.create_option(repository.USER_TYPES, {"name": name})
            created.append(f"user_type:{name}")

    for name in DEFAULT_PLATFORMS:
        if not repository.get_option_by_name(repository.PLATFORMS, name):
            repository.create_option(repository.PLATFORMS, {"name": name})
            created.append(f"platform:{name}")

    for name in DEFAULT_TICKET_CATEGORIES:
        if not repository.get_option_by_name(repository.TICKET_CATEGORIES, name):
            repository.create_option(repository.TICKET_CATEGORIES, {"name": name})
            created.append(f"ticket_category:{name}")

    for priority in DEFAULT_PRIORITIES:
        if not repository.get_option_by_name(repository.TICKET_PRIORITIES, priority["name"]):
            repository.create_option(repository.TICKET_PRIORITIES, priority)
            created.append(f"priority:{priority['name']}")

    for key, description in DEFAULT_WHATSAPP_TEMPLATES.items():
        if not repository.get_template_by_key(key):
            repository.create_option(
                repository.WHATSAPP_TEMPLATES,
                {"key": key, "karix_template_id": None, "description": description},
            )
            created.append(f"whatsapp_template:{key}")

    for rule in DEFAULT_SLA_RULES:
        if not repository.get_sla_rule_for_priority(rule["priority"]):
            repository.create_option(repository.SLA_RULES, rule)
            created.append(f"sla_rule:{rule['priority']}")

    return created
