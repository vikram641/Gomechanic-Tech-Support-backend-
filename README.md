# GoMechanic Tech Support — Backend

FastAPI + MongoDB (`pymongo`) + JWT API for the GoMechanic tech support
ticketing system. The React frontend is a separate project and is not in
this repo.

```
.
├── backend/                  FastAPI API (the active backend)
├── backend_django_archived/  Old Django + DRF version, kept for reference only
├── docs/                     API reference and integration notes
└── CLAUDE.md                 Project context for AI-assisted development
```

See [`backend/README.md`](backend/README.md) for the project layout, auth
model and API overview.

## Prerequisites

- Python 3
- A MongoDB connection string (MongoDB Atlas or a local MongoDB server)

## Setup

Run everything from the `backend/` folder.

```bash
cd backend

# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your local environment file
cp .env.example .env
```

Open `backend/.env` and set at least:

| Variable | Description |
|---|---|
| `MONGO_URI` | Your MongoDB connection string. Required. |
| `MONGO_DB_NAME` | Database name. Defaults to `gomechanic_tech_support`. |
| `JWT_SECRET` | Long random string used to sign tokens. Change it from the default. |
| `CORS_ALLOWED_ORIGINS` | Frontend origins allowed to call the API. Defaults to the Vite dev server on port 5173. |

`.env` is git-ignored. Never commit it or paste real values into the README
or any other tracked file.

### Seed the database

Run these once after the first setup. They are safe to re-run.

```bash
# Default dropdown values: user types, platforms, ticket categories,
# priorities, WhatsApp template keys and SLA rules
python -m scripts.seed_defaults

# First admin account (prompts for a password)
python -m scripts.create_admin --name "Admin" --email admin@gomechanic.in
```

To skip the password prompt, pass `--password "..."`. Avoid this in shared
shell history.

## Run

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

- API: http://127.0.0.1:8000
- Interactive API docs (Swagger UI): http://127.0.0.1:8000/docs
- Uploaded ticket attachments are served from `/media/`.

If you run the server without activating the virtual environment, use the
interpreter directly:

```bash
.venv/bin/python -m uvicorn main:app --reload --port 8000
```

## Notes

- **WhatsApp (Karix):** Until `KARIX_API_KEY` and `KARIX_SOURCE_ADDRESS`
  are set, WhatsApp sends are logged as skipped and do not block ticket
  workflows. See `docs/KARIX_INTEGRATION_REQUIREMENTS.md`.
- **API reference:** Endpoint details are in `docs/API.md`. Keep it updated
  when endpoints change, since the frontend is built against it.
- **Previous `backend/venv/`:** The local `venv/` folder is git-ignored. Use
  `.venv/` as shown above for a fresh setup.
