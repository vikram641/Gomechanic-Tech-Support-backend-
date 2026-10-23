# GoMechanic Tech Support — Backend

Django + Django REST Framework API. All persistence goes through **MongoDB via
`pymongo`** directly (no Django ORM models) — auth, tickets, configuration,
and notification logs are plain Mongo documents accessed through a thin
repository layer per app. Auth is stateless **JWT** issued/verified with
`PyJWT` against Mongo-backed user documents (no Django `User` model).

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: paste your real MONGO_URI (and MONGO_DB_NAME if you want a
# different database name than the default `gomechanic_tech_support`)

python manage.py migrate      # only creates local sqlite tables that DRF's
                               # internals need (contenttypes/auth) — no
                               # actual app data lives there
python manage.py seed_defaults   # seeds default user types, platforms,
                                  # ticket categories, priorities, WhatsApp
                                  # template keys, and SLA rules into Mongo
python manage.py create_admin --name "Admin" --email admin@gomechanic.in
                                  # bootstraps the first admin account
                                  # (prompts for a password)

python manage.py runserver
```

## Project layout

```
techsupport/        Django settings, root urls, wsgi/asgi
core/                mongo.py (client), jwt_utils.py, authentication.py,
                      permissions.py, pagination.py, utils.py, exceptions.py
apps/
  accounts/           auth (register/login/refresh/me) + admin user mgmt
  configuration/       dynamic dropdowns: user types, platforms, ticket
                        categories, priorities, WhatsApp template keys, SLA rules
  tickets/             ticket CRUD, assignment, status workflow, notes,
                        history, CSAT
  notifications/       Karix WhatsApp service + inbound webhook + logs
  analytics/           reports summary + Excel/PDF export
```

## Auth model

Three roles: `admin`, `support_engineer`, `user` (a ticket-raising CR /
Garage Owner / etc.). `POST /api/auth/register` is public and always creates
a `user`; only an admin can create `support_engineer` / `admin` accounts via
`POST /api/users/`. Every protected endpoint expects `Authorization: Bearer
<access token>`.

## API reference

Full endpoint-by-endpoint reference (auth rules, request/response bodies,
curl examples, ticket status graph) lives in
[`../docs/API.md`](../docs/API.md) — that's the source of truth the React
frontend gets built against. Quick map of what's mounted where:

| Prefix | App | Covers |
|---|---|---|
| `/api/auth/` | `accounts` | register, login, refresh, me |
| `/api/users/` | `accounts` | admin user management |
| `/api/config/` | `configuration` | user types, platforms, categories, priorities, WhatsApp templates, SLA rules |
| `/api/tickets/` | `tickets` | ticket CRUD, assign, status, notes, history, CSAT |
| `/api/notifications/` | `notifications` | WhatsApp send logs, Karix inbound webhook |
| `/api/analytics/` | `analytics` | summary, Excel export, PDF export |

See also [`../CLAUDE.md`](../CLAUDE.md) for the architectural conventions
(no Django ORM, repository pattern, JWT auth model, status-transition graph)
to follow when extending any of these.

## WhatsApp (Karix)

`apps/notifications/karix_client.py` wraps the send call; `apps/tickets/views.py`
fires it at every workflow trigger point from the FRD (created, assigned, in
progress, info required, resolved, CSAT check, reopened, closed). Until
`KARIX_API_KEY` / `KARIX_SOURCE_ADDRESS` are set in `.env` and each
`whatsapp_templates` document has a real `karix_template_id`, sends are
logged as `SKIPPED_NOT_CONFIGURED` instead of actually calling out — nothing
in the ticket workflow blocks on this. Once real credentials and template
IDs arrive:

1. Set `KARIX_API_KEY`, `KARIX_SOURCE_ADDRESS`, `KARIX_API_BASE_URL` in `.env`.
2. `PATCH /api/config/whatsapp-templates/<id>/` with each template's real
   `karix_template_id`.
3. Confirm the actual request/response shape in Karix's docs against
   `_build_payload` / the response-field read in `karix_client.py`, and the
   inbound webhook payload field names in `apps/notifications/views.py`
   (`KarixWebhookSerializer` currently assumes `{source, text}`).

## What's deliberately not here yet

- No rate limiting / throttling on public endpoints (`register`, the Karix
  webhook) — add DRF throttle classes before this goes to production traffic.
- Attachments are saved to local disk (`MEDIA_ROOT`) — swap
  `default_storage` for S3/GCS via `django-storages` if this needs to run on
  more than one app server.
- The Karix webhook has no signature/secret verification since Karix's
  signing scheme wasn't available yet — see the note in `KarixWebhookView`.
