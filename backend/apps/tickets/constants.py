OPEN = "Open"
ASSIGNED = "Assigned"
IN_PROGRESS = "In Progress"
WAITING_FOR_USER = "Waiting for User Response"
ON_HOLD = "On Hold"
RESOLVED = "Resolved"
REOPENED = "Reopened"
CLOSED = "Closed"

ALL_STATUSES = (
    OPEN,
    ASSIGNED,
    IN_PROGRESS,
    WAITING_FOR_USER,
    ON_HOLD,
    RESOLVED,
    REOPENED,
    CLOSED,
)

# Which statuses a ticket in a given status may legally move to next.
# Resolved -> Closed/Reopened is normally driven by the CSAT WhatsApp reply
# (see notifications app) but engineers can also record it manually.
ALLOWED_TRANSITIONS = {
    OPEN: {ASSIGNED, IN_PROGRESS, ON_HOLD, CLOSED},
    ASSIGNED: {IN_PROGRESS, WAITING_FOR_USER, ON_HOLD, RESOLVED},
    IN_PROGRESS: {WAITING_FOR_USER, ON_HOLD, RESOLVED, ASSIGNED},
    WAITING_FOR_USER: {IN_PROGRESS, ON_HOLD, RESOLVED},
    ON_HOLD: {IN_PROGRESS, ASSIGNED, RESOLVED},
    RESOLVED: {CLOSED, REOPENED},
    REOPENED: {ASSIGNED, IN_PROGRESS},
    CLOSED: {REOPENED},
}

# Status change -> WhatsApp template key to fire (apps.notifications). Ticket
# creation fires TICKET_CREATED directly in the create flow, not from here.
STATUS_TEMPLATE_MAP = {
    ASSIGNED: "TICKET_ASSIGNED",
    IN_PROGRESS: "TICKET_IN_PROGRESS",
    WAITING_FOR_USER: "INFO_REQUIRED",
    RESOLVED: "TICKET_RESOLVED",
    REOPENED: "TICKET_REOPENED",
    CLOSED: "TICKET_CLOSED",
}

DEFAULT_PRIORITY = "Medium"
