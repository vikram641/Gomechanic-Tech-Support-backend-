# GoMechanic Tech Support — Backend

FastAPI API. All persistence goes through **MongoDB via `pymongo`** directly
(no ORM) — auth, tickets, configuration, and notification logs are plain
Mongo documents accessed through a thin repository layer per app. Auth is
stateless **JWT** issued/verified with `PyJWT` against Mongo-backed user
documents.

This backend previously ran on Django + DRF; that implementation has been
retired and archived at `../backend_django_archived` for reference. This
FastAPI implementation is now the only backend for this project.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: paste your real MONGO_URI (and MONGO_DB_NAME if you want a
# different database name than the default `gomechanic_tech_support`)

python -m scripts.seed_defaults   # seeds default user types, platforms,
                                   # ticket categories, priorities, WhatsApp
                                   # template keys, and SLA rules into Mongo
python -m scripts.create_admin --name "Admin" --email admin@gomechanic.in
                                   # bootstraps the first admin account
                                   # (prompts for a password)

uvicorn main:app --reload --port 8000
```

Interactive API docs: http://127.0.0.1:8000/docs

## Project layout

```
main.py               FastAPI() app: CORS, routers, /media static mount, exception handlers
core/                  config.py (settings), mongo.py (client), security.py (password hashing),
                       jwt_utils.py, deps.py (auth/role dependencies), pagination.py, errors.py
apps/
  accounts/            auth (register/login/refresh/me) + admin user mgmt
  configuration/        dynamic dropdowns: user types, platforms, ticket
                        categories, priorities, WhatsApp template keys, SLA rules
  tickets/              ticket CRUD, assignment, status workflow, notes,
                        history, CSAT, attachments
  notifications/        Karix WhatsApp client + inbound webhook + logs
  analytics/            reports summary + Excel/PDF export
scripts/               create_admin.py, seed_defaults.py (CLI entry points)
media/                 uploaded ticket attachments (uploads/tickets/<id>/<uuid>.<ext>)
```

## Auth model

Three roles: `admin`, `support_engineer`, `user` (a ticket-raising CR /
Garage Owner / etc.). `POST /api/auth/register` is public and always creates
a `user`; only an admin can create `support_engineer` / `admin` accounts via
`POST /api/users/`. Every protected endpoint expects `Authorization: Bearer
<access token>`.

## API reference

Full endpoint-by-endpoint reference (auth rules, request/response bodies,
error shapes) lives in `../docs/API.md` — keep it updated when endpoints
change, since the React frontend is built against it.

## WhatsApp (Karix)

`apps/notifications/karix_client.py`'s `KarixWhatsAppService` wraps the
Karix (Airtel IQ CPaaS) WhatsApp Business API. Real credentials and
per-template IDs were not available when this was built — sends degrade to
a logged `SKIPPED_NOT_CONFIGURED`/`SKIPPED_NO_TEMPLATE` no-op until both are
set, so the ticket workflow never blocks on WhatsApp delivery. See
`../docs/KARIX_INTEGRATION_REQUIREMENTS.md` for the full checklist of what's
needed from Karix's side before wiring up the real integration.

## What's deliberately not here yet

- No rate limiting/throttling on public endpoints (register, Karix webhook).
- Attachments are saved to local disk (`media/`) — would need S3/GCS for a
  multi-server deployment.
- The Karix webhook has no signature/secret verification yet.
