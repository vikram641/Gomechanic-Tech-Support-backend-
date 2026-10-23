# GoMechanic Tech Support Management System

Internal tool: users raise tech-support tickets, the support team assigns/
tracks/resolves them, WhatsApp notifies the user at each stage, and a
post-resolution satisfaction check auto-closes or reopens the ticket. Built
from a functional requirements doc covering ticket workflow, dynamic
admin-configurable dropdowns, WhatsApp automation, and analytics/reports.

## Repo layout

```
backend/                    FastAPI API (see backend/README.md for setup + run commands)
backend_django_archived/    Retired Django+DRF implementation, kept for reference only —
                             not run, not maintained, not wired into anything.
docs/                       API.md — full endpoint reference with request/response examples
```

The React frontend is a sibling project at
`../Gomechanic-Tech-Support-React` (separate repo/directory, not nested
here) — see its own `CLAUDE.md`/`README.md` for stack details (Vite + React +
TypeScript + Tailwind v4 + TanStack Query + Recharts). It was originally
built and verified end-to-end against the Django backend via a
mongomock-backed dev server (see "History" below); the backend has since
been rewritten in FastAPI against the same MongoDB data and the same
documented wire contract (`docs/API.md`), so the frontend should work
against either without changes.

## Stack decisions — read before changing architecture

- **No ORM.** Every persistence op goes through **`pymongo`** directly. Each
  app under `backend/apps/` has a `repository.py` that talks to MongoDB
  collections directly (`get_db().tickets`, `get_db().users`, etc.). Don't
  add an ORM; add a function to the relevant `repository.py` instead.
- **Auth is stateless JWT** via raw `PyJWT` (no framework auth library —
  there's no ORM-backed User model to hang one off of). See
  `backend/core/jwt_utils.py` (issue/decode) and `backend/core/deps.py` (the
  FastAPI dependencies that decode the bearer token, look the user up in
  Mongo, and enforce role checks). Three roles: `admin`, `support_engineer`,
  `user` (ticket-raiser — CR/Garage Owner/etc.).
- **Password hashing** is a from-scratch reimplementation of Django's
  PBKDF2 hasher format (`backend/core/security.py`) — kept byte-compatible
  with the hashes already stored in Mongo from when this ran on Django, so
  no user had to reset their password when the backend was rewritten. Don't
  swap to `passlib`/`bcrypt` without a migration plan for existing hashes.
- **WhatsApp is Karix** (Airtel IQ CPaaS), wrapped in
  `backend/apps/notifications/karix_client.py` (uses `httpx`). Real
  credentials and per-template IDs were not available when this was built —
  sends degrade to a logged `SKIPPED_NOT_CONFIGURED` no-op until both are
  set, so the ticket workflow never blocks on WhatsApp delivery.
  `KarixWhatsAppService` checks two independent things before a send is
  attempted, and either being missing produces the skip:
  1. **Account credentials** in `.env`: `KARIX_API_KEY` and
     `KARIX_SOURCE_ADDRESS` (the WhatsApp Business number registered with
     Karix) — `is_configured()` requires both. `KARIX_API_BASE_URL` already
     defaults to `https://api.karix.io`.
  2. **A `karix_template_id` on each of the 8 template records** (`key` in
     `TICKET_CREATED`, `TICKET_ASSIGNED`, `TICKET_IN_PROGRESS`,
     `INFO_REQUIRED`, `TICKET_RESOLVED`, `CSAT_CHECK`, `TICKET_REOPENED`,
     `TICKET_CLOSED`) — each must be a template pre-approved in your Karix
     dashboard (WhatsApp Business requires template pre-approval by Meta).
     Set via `PATCH /api/config/whatsapp-templates/<id>/
     {"karix_template_id": "..."}` or the Configuration UI. A template with
     `is_active: false` or a blank ID is also skipped.
  If you're asked to "wire up the real Karix integration," that means both
  of the above, **plus** double-checking `_build_payload()` in
  `karix_client.py` and the inbound webhook field names in
  `apps/notifications/router.py` (`KarixWebhookRequest` assumes
  `{source, text}`) against Karix's actual API docs — both were best-effort
  guesses at build time, not verified against real documentation. See
  `docs/KARIX_INTEGRATION_REQUIREMENTS.md` for the full checklist of what's
  needed from Karix's side (credentials, template approval, webhook
  contract, compliance questions) — that's the doc to hand to Karix or
  whoever owns that vendor relationship.
- MongoDB connection string lives in `backend/.env` (`MONGO_URI`,
  gitignored) — never hardcode it or ask the user to paste it into chat;
  they add it directly to the file.

## Conventions to follow when extending this backend

- One `apps/` package per bounded concern (`accounts`, `configuration`,
  `tickets`, `notifications`, `analytics`) — each has `repository.py`
  (pymongo access), `schemas.py` (Pydantic models for request/response
  bodies), `router.py` (FastAPI `APIRouter` with one route function per
  endpoint).
- Dropdown-style config (user types, platforms, categories, priorities,
  WhatsApp template keys, SLA rules) is soft-deleted (`is_active: false`),
  never hard-deleted — tickets may reference historical values. Follow the
  same pattern for any new configurable list. All six dropdown types share
  one generic router factory (`build_dropdown_router` in
  `apps/configuration/router.py`) — add a new dropdown type by calling that
  factory again, not by writing new route handlers.
- Every ticket status change goes through
  `apps/tickets/repository.update_status`, which enforces
  `ALLOWED_TRANSITIONS` in `apps/tickets/constants.py` and fires the mapped
  WhatsApp template via `STATUS_TEMPLATE_MAP`. Don't set `ticket.status`
  directly anywhere else — add new transitions to that map instead of
  bypassing it.
- **Tickets can be created two ways**: by a logged-in account
  (`POST /api/tickets/`, `created_by` set, staff-only visible if the role is
  `user`) or by a guest with no account at all
  (`POST /api/tickets/public`, no auth required, `created_by: null`, contact
  info captured directly on `created_by_snapshot` from the submitted
  `name`/`email`/`phone`). `apps/tickets/repository.create_ticket` branches
  on whether `creator` or `guest_name`/`guest_email`/`guest_phone` was
  passed — don't add a third path; extend that branch instead. The
  `/public` route **must stay declared separately** from `/{ticket_id}` in
  `apps/tickets/router.py` (see the comment there) even though FastAPI
  resolves the literal route correctly regardless of order, since the two
  routes differ by HTTP method anyway (POST vs GET).
- List endpoints use `core/pagination.py`'s `page_params` dependency +
  `build_page()` helper, which paginate a plain Python list the repository
  already fetched with Mongo `skip`/`limit` — there's no ORM
  queryset/pagination class involved, just plain functions.
- `core/utils.serialize_doc` / each app's `repository.to_public` helpers
  strip `_id` → `id` (string) and drop sensitive fields (e.g. `password`)
  before a Mongo doc reaches a Pydantic response model — always pass docs
  through the app's `to_public` before constructing a response schema.
- **Error contract**: DRF-style — field validation errors as
  `{"field_name": ["message"]}`, everything else as `{"detail": "message"}`,
  enforced via the exception handlers in `core/errors.py` (including a
  custom `RequestValidationError` handler that reshapes Pydantic's default
  422 body into this shape at 400, to preserve the same wire contract the
  React frontend was built against). Raise `AppError(message=..., field=...)`
  for business-logic errors instead of a bare `ValueError`, and
  `HTTPException` for standard 401/403/404s.

## History

This backend originally ran on Django + DRF (see
`backend_django_archived/` — retired, not run, kept for reference only). It
was rewritten in FastAPI, keeping the same MongoDB data, the same
`pymongo`-direct repository layer (ported essentially unchanged — it never
used the Django ORM to begin with), the same JWT auth scheme, and the same
documented wire contract in `docs/API.md`, so no data migration or frontend
changes were needed. Existing user passwords (hashed with Django's PBKDF2
format) remain valid under the new backend's `core/security.py`.

Before that rewrite, the frontend was built and verified end-to-end
(register → login → create ticket → assign → status workflow → CSAT
reopen/close loop → analytics) against the Django backend via a
mongomock-backed dev server, which surfaced and led to fixing three real
backend bugs:

1. **CORS default port.** Was `3000`; Vite's dev server defaults to `5173`.
   If you add another frontend dev server on a different port, add its
   origin to `CORS_ALLOWED_ORIGINS` too.
2. **Configuration reads (`/api/config/*`) are public, not merely "any
   authenticated user."** The self-registration form needs to read
   `user-types` before the visitor has an account/token — there's no other
   way to populate that dropdown pre-signup. Writes remain admin-only.
3. **`GET /api/users/` allows support staff (admin or support_engineer),
   not just admins.** An engineer needs this list to populate the "assign
   ticket to" dropdown — restricting it to admins only would silently break
   ticket assignment for every non-admin engineer. `POST/PATCH/DELETE` on
   `/api/users/` remain admin-only (those actually create/modify accounts).
4. **A stale/expired/invalid JWT must not hard-fail a public route.** The
   auth dependency (`core/deps.py`'s `get_current_user_optional`) returns
   `None` on any decode failure — missing header, malformed, expired,
   wrong-type, user not found/inactive — rather than raising, so a stale
   token left in a browser's `localStorage` doesn't 401 pages like
   `/raise-ticket` or registration that don't require auth at all. Routes
   that actually require auth still enforce it via `get_current_user` /
   `require_admin` / `require_support_staff`.

## Docs

- `backend/README.md` — setup, run commands, project layout, short API table.
- `docs/API.md` — the full API reference: every endpoint, auth requirement,
  request/response bodies, and example curl calls. Keep this updated when
  endpoints change — it's what the React frontend is built against.
