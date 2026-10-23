# API Reference — GoMechanic Tech Support Management System

Base URL (local dev): `http://127.0.0.1:8000`

All endpoints are prefixed `/api/`. All request/response bodies are JSON
unless noted (ticket creation accepts `multipart/form-data` for file
attachments).

## Conventions

### Auth

Send `Authorization: Bearer <access_token>` on every endpoint except the ones
explicitly marked **Public** below. Get a token pair from `POST
/api/auth/login` or `POST /api/auth/register`.

| Role | Who | Can do |
|---|---|---|
| `user` | Ticket raiser (CR, Garage Owner, Chat Support, etc.) | Create tickets, view/search only their own tickets, view own ticket history |
| `support_engineer` | Support team member | Everything a `user` can, plus: view/filter all tickets, assign, change status, add internal notes, record CSAT overrides, view analytics & notification logs |
| `admin` | Full admin | Everything `support_engineer` can, plus: manage users (create engineers/admins), manage all configuration (dropdowns, SLA rules, WhatsApp templates) |

Endpoints below list the **minimum** role required; higher roles listed to
their left in the table are always also allowed unless stated otherwise.

### Pagination

List endpoints accept `?page=1&page_size=20` (`page_size` capped at 200) and
respond with:

```json
{
  "count": 137,
  "page": 1,
  "page_size": 20,
  "total_pages": 7,
  "results": [ /* ... */ ]
}
```

### Errors

- Request validation failures → `400` with a field-keyed shape:
  `{"field_name": ["error message"]}`.
- Everything else (not found, business-rule violations, auth failures) →
  `{"detail": "human-readable message"}` with an appropriate status code
  (`400`, `401`, `403`, `404`).

### IDs

Every resource returns `id` as a string (Mongo `ObjectId` stringified) — use
that string in subsequent path params. Tickets are the one exception: `<ticket_id>`
path params accept **either** the Mongo `id` **or** the human-readable
`ticket_id` code (e.g. `GM-2001`).

---

## Auth — `/api/auth/`

### `POST /api/auth/register` — Public

Self sign-up for ticket-raising end users. Always creates role `user`.

Request:
```json
{
  "name": "Vikram Singh",
  "email": "vikram@example.com",
  "phone": "+919999900000",
  "password": "pass12345",
  "user_type": "Garage Owner"
}
```
`user_type` must match an active value from `GET /api/config/user-types/`.

Response `201`:
```json
{
  "user": {
    "id": "665f1a2b3c4d5e6f7a8b9c0d",
    "name": "Vikram Singh",
    "email": "vikram@example.com",
    "phone": "+919999900000",
    "role": "user",
    "user_type": "Garage Owner",
    "is_active": true,
    "created_at": "2026-07-18T14:40:52.571000+05:30"
  },
  "access": "<jwt>",
  "refresh": "<jwt>"
}
```
`400` if the email already exists or `user_type` is unknown/inactive.

### `POST /api/auth/login` — Public

Request: `{"email": "...", "password": "..."}`
Response `200`: same shape as register (`user`, `access`, `refresh`).
`401` on bad credentials, `403` if the account is deactivated.

### `POST /api/auth/refresh` — Public

Request: `{"refresh": "<refresh jwt>"}`
Response `200`: `{"access": "<new jwt>"}`
`401` if the refresh token is expired/invalid or the user no longer exists/is inactive.

### `GET /api/auth/me` — Authenticated

Returns the caller's own user object (same shape as `register`'s `user`).

### `PATCH /api/auth/me` — Authenticated

Partial update. Body: any of `{"name", "phone", "is_active", "password"}`.
Note: a non-admin can technically flip their own `is_active` here today —
if you need to lock that down, restrict it in `UserUpdateSerializer`/`MeView`.

---

## Users — `/api/users/`

### `GET /api/users/` — staff (admin or support_engineer)

Query params: `role` (`admin`|`support_engineer`|`user`), `search`
(matches name/email, case-insensitive), plus pagination params. Open to any
support staff, not just admins — an engineer needs this list to see who's
available to assign/reassign a ticket to.

### `POST /api/users/` — admin only

Create a support engineer, admin, or a manually-added end user.

Request:
```json
{
  "name": "R. Verma",
  "email": "rverma@gomechanic.in",
  "phone": "+919876500000",
  "password": "engineerpass1",
  "role": "support_engineer",
  "user_type": null
}
```
`role` defaults to `support_engineer` if omitted. `user_type` is required
when `role` is `"user"`.

Response `201`: the created user object.

### `GET /api/users/<id>` — admin only

Response `200`: user object. `404` if not found.

### `PATCH /api/users/<id>` — admin only

Partial update — same fields as `PATCH /api/auth/me`.

### `DELETE /api/users/<id>` — admin only

Soft-deactivates (`is_active: false`) — never hard-deletes. Response `204`.

---

## Configuration — `/api/config/`

Six dropdown-style collections, each with the same list/create/detail shape.
**Reads are public — no auth required** (the self-registration form needs to
read `user-types` before the visitor has an account/token, and this is
non-sensitive reference data); **writes are admin-only**.

| Collection | Path prefix | Schema |
|---|---|---|
| User Types | `user-types/` | `{name, is_active}` |
| Platforms | `platforms/` | `{name, is_active}` |
| Ticket Categories | `ticket-categories/` | `{name, is_active}` |
| Ticket Priorities | `ticket-priorities/` | `{name, level, is_active}` — lower `level` = more urgent |
| WhatsApp Templates | `whatsapp-templates/` | `{key, karix_template_id, description, is_active}` |
| SLA Rules | `sla-rules/` | `{priority, response_time_minutes, resolution_time_minutes, is_active}` |

### `GET /api/config/<collection>/`

Query param `?active_only=false` to include inactive/soft-deleted values
(default `true`, i.e. only active ones — this is what a ticket-creation form
should call).

Example (`GET /api/config/user-types/`), response `200`:
```json
[
  {"id": "665f...", "name": "CR", "is_active": true, "created_at": "...", "updated_at": "..."},
  {"id": "665f...", "name": "Central CR", "is_active": true, "created_at": "...", "updated_at": "..."},
  {"id": "665f...", "name": "Lead Call Center", "is_active": true, "created_at": "...", "updated_at": "..."},
  {"id": "665f...", "name": "Chat Support", "is_active": true, "created_at": "...", "updated_at": "..."},
  {"id": "665f...", "name": "Garage Owner", "is_active": true, "created_at": "...", "updated_at": "..."},
  {"id": "665f...", "name": "Service Adviser", "is_active": true, "created_at": "...", "updated_at": "..."}
]
```

Example (`GET /api/config/whatsapp-templates/?active_only=false`):
```json
[
  {
    "id": "665f...",
    "key": "TICKET_CREATED",
    "karix_template_id": null,
    "description": "Sent when a user raises a new ticket.",
    "is_active": true,
    "created_at": "...",
    "updated_at": "..."
  }
]
```
Template keys seeded by default: `TICKET_CREATED`, `TICKET_ASSIGNED`,
`TICKET_IN_PROGRESS`, `INFO_REQUIRED`, `TICKET_RESOLVED`, `CSAT_CHECK`,
`TICKET_REOPENED`, `TICKET_CLOSED`.

### `POST /api/config/<collection>/` — admin only

Body matches the collection's schema (see table above; `is_active` optional,
defaults `true`). `400` if the unique field (`name`, or `key` for WhatsApp
templates, or `priority` for SLA rules) already exists.

### `GET /api/config/<collection>/<id>/`

Single option. `404` if not found.

### `PATCH /api/config/<collection>/<id>/` — admin only

Partial update, e.g. to fill in a real `karix_template_id`:
```json
{"karix_template_id": "waba_template_abc123"}
```

### `DELETE /api/config/<collection>/<id>/` — admin only

Soft-deactivates (`is_active: false`). Response `204`.

---

## Tickets — `/api/tickets/`

### `GET /api/tickets/`

Query params: `status`, `user_type`, `platform`, `priority`, `assigned_to`
(user id), `created_by` (user id), `date_from` / `date_to` (ISO date/datetime,
filters on `created_at`), `search` (matches `ticket_id`, `title`, or the
creator's name/email), plus pagination params.

**A caller with role `user` is always auto-scoped to their own tickets** —
`created_by`/other filters they pass are ignored for that purpose; they only
ever see tickets they raised.

Response `200` (paginated envelope, each result is the light list shape):
```json
{
  "count": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1,
  "results": [
    {
      "id": "665f...",
      "ticket_id": "GM-2001",
      "title": "Unable to login to CR App",
      "user_type": "Garage Owner",
      "platform": "CR App",
      "category": null,
      "priority": "Medium",
      "status": "Assigned",
      "assigned_to_snapshot": {"name": "R. Verma", "email": "rverma@gomechanic.in"},
      "created_by_snapshot": {"name": "Vikram Singh", "email": "vikram@example.com", "phone": "+919999900000"},
      "reopened_count": 0,
      "created_at": "2026-07-18T14:40:52.571000+05:30",
      "updated_at": "2026-07-18T14:41:10.100000+05:30"
    }
  ]
}
```

### `POST /api/tickets/` — Authenticated

`multipart/form-data` (so `attachments` can carry files) with fields:

| Field | Required | Notes |
|---|---|---|
| `title` | yes | |
| `description` | yes | |
| `user_type` | yes | must be an active `user-types` value |
| `platform` | yes | must be an active `platforms` value |
| `category` | no | must be an active `ticket-categories` value if given |
| `priority` | no | must be an active `ticket-priorities` value if given; defaults to `Medium` |
| `login_credentials` | no | free-text note field for credentials needed to reproduce the issue |
| `attachments` | no | one or more files (screenshots etc.) |

```bash
curl -X POST http://127.0.0.1:8000/api/tickets/ \
  -H "Authorization: Bearer $ACCESS" \
  -F "title=Unable to login to CR App" \
  -F "description=Getting OTP error on every attempt" \
  -F "user_type=Garage Owner" \
  -F "platform=CR App" \
  -F "attachments=@screenshot.png"
```

Response `201`: the full ticket detail shape (see `GET /api/tickets/<id>`
below). Fires the `TICKET_CREATED` WhatsApp template to the creator's phone.

### `POST /api/tickets/public` — Public (no login required)

The no-login submission form — meant to be a URL shared directly with
whoever is facing the issue, so they don't need an account. Same fields as
`POST /api/tickets/` above, **plus** contact details since there's no logged-in
user to pull them from:

| Field | Required | Notes |
|---|---|---|
| `name` | yes | the reporter's name |
| `email` | yes | the reporter's email |
| `phone` | yes | the reporter's WhatsApp number — status updates go here |
| ...all fields from `POST /api/tickets/` above | | |

```bash
curl -X POST http://127.0.0.1:8000/api/tickets/public \
  -F "name=Rohit Sharma" \
  -F "email=rohit@example.com" \
  -F "phone=+919876543210" \
  -F "title=App crashes on opening job card" \
  -F "description=Every time I open a job card the app closes." \
  -F "user_type=CR" \
  -F "platform=CR App"
```

Response `201`: same ticket detail shape, but `created_by: null` — the
ticket has no linked account, just the `created_by_snapshot` built from
`name`/`email`/`phone`. Since there's no account, the reporter can't later
log in to track it via `GET /api/tickets/<id>` (that stays owner-or-staff) —
tracking status is via the WhatsApp updates only, or a staff member looking
it up.

### `GET /api/tickets/<ticket_id>` — owner or staff

Response `200`, full detail:
```json
{
  "id": "665f...",
  "ticket_id": "GM-2001",
  "title": "Unable to login to CR App",
  "description": "Getting OTP error on every attempt",
  "user_type": "Garage Owner",
  "platform": "CR App",
  "category": null,
  "priority": "Medium",
  "status": "Resolved",
  "login_credentials": null,
  "attachments": [
    {"filename": "screenshot.png", "url": "/media/uploads/tickets/GM-2001/ab12cd34.png", "content_type": "image/png", "uploaded_at": "..."}
  ],
  "created_by": "665f1a2b3c4d5e6f7a8b9c0d",
  "created_by_snapshot": {"name": "Vikram Singh", "email": "vikram@example.com", "phone": "+919999900000"},
  "assigned_to": "665f1a2b3c4d5e6f7a8b9c0e",
  "assigned_to_snapshot": {"name": "R. Verma", "email": "rverma@gomechanic.in"},
  "internal_notes": [
    {"author_id": "665f...", "author_name": "R. Verma", "note": "Reproduced on staging.", "created_at": "..."}
  ],
  "csat_status": "pending",
  "reopened_count": 0,
  "first_response_at": "2026-07-18T14:45:00+05:30",
  "resolved_at": "2026-07-18T15:10:00+05:30",
  "closed_at": null,
  "created_at": "2026-07-18T14:40:52.571000+05:30",
  "updated_at": "2026-07-18T15:10:00+05:30"
}
```
`404` if not found. `403` if you're a `user` and it's not your ticket.

### `PATCH /api/tickets/<ticket_id>/assign` — staff only

Request: `{"engineer_id": "665f1a2b3c4d5e6f7a8b9c0e"}`
(`engineer_id` must be an active `admin` or `support_engineer` account.)

Response `200`: updated ticket detail. If the ticket was `Open`, it also
moves to `Assigned`; if it was any other status, the status is left as-is
(re-assigning doesn't reset progress). Fires `TICKET_ASSIGNED`.

### `PATCH /api/tickets/<ticket_id>/status` — staff only

Request: `{"status": "In Progress", "note": "optional free-text note"}`

Valid `status` values: `Open`, `Assigned`, `In Progress`, `Waiting for User
Response`, `On Hold`, `Resolved`, `Reopened`, `Closed`.

Transitions are validated against an allowed-transition graph — e.g. you
can't jump straight from `Open` to `Resolved`. `400 {"detail": "Cannot move a
ticket from 'X' to 'Y'."}` if the transition isn't allowed. See
`backend/apps/tickets/constants.py::ALLOWED_TRANSITIONS` for the full graph.

Side effects:
- `In Progress` (first time only) stamps `first_response_at`.
- `Resolved` stamps `resolved_at`, sets `csat_status: "pending"`, fires
  `TICKET_RESOLVED` **and** `CSAT_CHECK` (the "are you satisfied?" message).
- `Closed` stamps `closed_at`, fires `TICKET_CLOSED`.
- `Reopened` increments `reopened_count`, clears `resolved_at`/`closed_at`,
  fires `TICKET_REOPENED`.

Response `200`: updated ticket detail.

### `POST /api/tickets/<ticket_id>/notes` — staff only

Internal note, never shown to the end user. Request: `{"note": "..."}`
Response `201`: updated ticket detail (with the note appended to `internal_notes`).

### `GET /api/tickets/<ticket_id>/history` — owner or staff

Response `200`:
```json
{
  "activity_log": [
    {"actor_id": null, "actor_name": "Vikram Singh", "action": "ticket_created", "from_status": null, "to_status": "Open", "note": null, "created_at": "..."},
    {"actor_id": "665f...", "actor_name": "Admin", "action": "assigned", "from_status": "Open", "to_status": "Assigned", "note": "Assigned to R. Verma", "created_at": "..."},
    {"actor_id": "665f...", "actor_name": "R. Verma", "action": "status_changed", "from_status": "Assigned", "to_status": "In Progress", "note": null, "created_at": "..."}
  ]
}
```

### `POST /api/tickets/<ticket_id>/csat-response` — staff only

Manual/internal recording of the user's WhatsApp satisfaction reply (the
Karix inbound webhook calls the same underlying logic automatically — use
this endpoint only to record it by hand, e.g. if the user replied by phone
instead of WhatsApp).

Request: `{"satisfied": true}` or `{"satisfied": false}`
- `true` → ticket moves to `Closed`, fires `TICKET_CLOSED`.
- `false` → ticket moves to `Reopened`, fires `TICKET_REOPENED`.

`400 {"detail": "CSAT response can only be recorded for a Resolved ticket."}`
if the ticket isn't currently `Resolved`.

---

## Notifications — `/api/notifications/`

### `GET /api/notifications/logs/` — staff only

Every WhatsApp send attempt, sent or not. Query params: `ticket_id`,
`status` (`SENT` | `FAILED` | `SKIPPED_NOT_CONFIGURED` | `SKIPPED_NO_TEMPLATE`),
plus pagination.

```json
{
  "count": 3,
  "results": [
    {
      "id": "665f...",
      "ticket_id": "GM-2001",
      "template_key": "TICKET_CREATED",
      "to_phone": "+919999900000",
      "status": "SKIPPED_NOT_CONFIGURED",
      "karix_message_id": null,
      "error": null,
      "created_at": "..."
    }
  ]
}
```

### `POST /api/notifications/webhook/karix` — Public

Inbound WhatsApp reply from Karix. **The exact field names here
(`source`, `text`) are a best-effort placeholder** — confirm against Karix's
actual webhook payload once available and adjust
`KarixWebhookSerializer`/`views.py` accordingly. No signature verification
yet; add a shared-secret header or IP allowlist before this is exposed
publicly.

Request (placeholder shape):
```json
{"source": "+919999900000", "text": "Satisfied"}
```

Behavior: finds the most recent `Resolved` ticket with `csat_status:
"pending"` for that phone number, interprets `text` as satisfied / not
satisfied (recognizes `"satisfied"`, `"yes"`, `"resolved"` vs. `"not
satisfied"`, `"not resolved"`, `"no"` — case-insensitive), and records the
response exactly like `POST /api/tickets/<id>/csat-response`.

Response `200`: `{"ticket_id": "GM-2001", "status": "Closed"}`
`400` if the reply text couldn't be interpreted. `404` if no ticket for that
phone is currently awaiting a CSAT reply.

---

## Analytics — `/api/analytics/` (staff only)

### `GET /api/analytics/summary`

Query params: `date_from`, `date_to` (ISO date/datetime; both optional —
omit for all-time).

```json
{
  "total_tickets": 1284,
  "tickets_by_status": {"Open": 12, "Assigned": 8, "In Progress": 20, "Resolved": 15, "Closed": 1200, "Reopened": 29},
  "tickets_by_platform": {"CR App": 800, "Garage Dashboard": 300, "Master Lead Dashboard": 184},
  "tickets_by_user_type": {"Garage Owner": 700, "CR": 400, "Service Adviser": 184},
  "resolved_per_engineer": [{"engineer": "R. Verma", "resolved_count": 210}, {"engineer": "S. Iyer", "resolved_count": 190}],
  "avg_resolution_time_hours": 4.2,
  "avg_first_response_time_minutes": 18.5,
  "reopened_tickets": 29,
  "pending_tickets": 40,
  "csat": {"satisfied": 1100, "not_satisfied": 105, "csat_percentage": 91.3},
  "sla_compliance": {"compliant": 1180, "total": 1215, "sla_percentage": 97.1},
  "daily_trend": [{"period": "2026-07-17", "count": 42}, {"period": "2026-07-18", "count": 51}],
  "weekly_trend": [{"period": "2026-W28", "count": 280}, {"period": "2026-W29", "count": 305}],
  "monthly_trend": [{"period": "2026-06", "count": 1120}, {"period": "2026-07", "count": 1284}]
}
```

`sla_compliance` is computed by comparing each resolved ticket's actual
`resolved_at - created_at` duration against its priority's
`resolution_time_minutes` from `/api/config/sla-rules/`; tickets whose
priority has no SLA rule configured are excluded from both numerator and
denominator.

### `GET /api/analytics/export/excel`

Same `date_from`/`date_to` params. Returns a `.xlsx` file
(`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)
with sheets: Overview, By Status, By Platform, By User Type, Resolved Per
Engineer, Daily Trend.

### `GET /api/analytics/export/pdf`

Same params. Returns a formatted `.pdf` (`Content-Type: application/pdf`)
with the same overview + by-status/platform/engineer tables.

---

## Ticket status reference

| Status | Meaning | Can move to |
|---|---|---|
| `Open` | Created, awaiting assignment | Assigned, In Progress, On Hold, Closed |
| `Assigned` | Routed to an engineer | In Progress, Waiting for User Response, On Hold, Resolved |
| `In Progress` | Engineer actively investigating | Waiting for User Response, On Hold, Resolved, Assigned |
| `Waiting for User Response` | Additional info requested | In Progress, On Hold, Resolved |
| `On Hold` | Paused pending a dependency | In Progress, Assigned, Resolved |
| `Resolved` | Fix applied, awaiting CSAT confirmation | Closed, Reopened |
| `Reopened` | User wasn't satisfied, back for rework | Assigned, In Progress |
| `Closed` | Confirmed resolved by the user | Reopened |
