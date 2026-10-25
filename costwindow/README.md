# CostWindow

Tracks every AI call, sets a monthly budget per process, and refuses the next call when a process goes over it.

## What's here

- `backend/` is the FastAPI app: auth, the drop-in proxy, ingest, budgets and the kill switch. `backend/migrations/` has the database schema to run in Supabase.
- `frontend/` is the React dashboard.
- `sdk/` is the Python client (`.log()`, `.wrap_anthropic()`, `.wrap_openai()`).
- `docs/troubleshooting/` has notes on the problems I hit and how I fixed them.

## What you need

- A Supabase project. Run the files in `backend/migrations/` in order in the SQL editor.
- Somewhere to host the backend (I used Railway) and the frontend (any static host).
- Copy `.env.example` to `backend/.env` and fill in: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `SECRET_KEY`, `BACKEND_URL`, `FRONTEND_URL`.
- Optional: `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` if you want paid plans, and `MAILERSEND_API_KEY`, `MAILERSEND_FROM_EMAIL`, `MAILERSEND_FROM_NAME` for email.
- In `frontend/`, create `.env.local` with `VITE_API_URL` pointing at your backend.

## Run it locally

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
pytest -v            # unit tests, no database needed

cd ../frontend
npm install
npm run dev
```

Provider prices live in `backend/app/pricing.py`. Check them against each provider's current rate card before you rely on the budgets.
