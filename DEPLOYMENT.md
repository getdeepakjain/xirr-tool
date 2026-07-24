# Deployment guide

This app is deployed as **two pieces**:

| Piece | Where | Why |
|-------|-------|-----|
| **Frontend** (React/Vite SPA) | **Vercel (Hobby)** | Static build, free, fast CDN |
| **Backend** (FastAPI + SQLite) | **Render / Railway / Fly.io** | Needs a long-lived process + persistent storage that Vercel's serverless functions don't provide |

The frontend talks to the backend over HTTPS using its absolute URL
(`VITE_BACKEND_URL`), and the backend allows that origin via `FRONTEND_ORIGINS`
(CORS). Auth uses JWT bearer tokens (stored in `localStorage`), so there are no
cross-site cookie issues for the main app.

Deploy the **backend first** so you know its URL, then the frontend, then come
back and fill the backend's `FRONTEND_ORIGINS` / `FRONTEND_URL` with the Vercel
domain.

---

## 1. Backend

Pick ONE host. All three keep your SQLite database on a persistent volume, so
the app runs essentially unchanged. (Prefer Postgres? See the note at the end.)

### Option A — Fly.io (free volume, SQLite unchanged)

Config lives in [`backend/fly.toml`](backend/fly.toml) and
[`backend/Dockerfile`](backend/Dockerfile).

```bash
cd backend
fly launch --no-deploy            # or `fly apps create xirr-backend`; keep the fly.toml
fly volumes create xirr_data --size 1 --region <your-region>   # must match primary_region
fly secrets set \
  SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')" \
  FRONTEND_ORIGINS="https://YOUR-APP.vercel.app" \
  FRONTEND_URL="https://YOUR-APP.vercel.app" \
  BACKEND_BASE_URL="https://xirr-backend.fly.dev"
fly deploy
```

`DATABASE_URL=sqlite:////data/portfolio.sqlite3` is already set in `fly.toml`,
pointing at the mounted volume.

### Option B — Render (Blueprint)

Config lives in [`render.yaml`](render.yaml).

1. Push this repo to GitHub.
2. Render → **New +** → **Blueprint** → select the repo. It reads `render.yaml`.
3. Fill the `sync: false` env vars in the dashboard (`FRONTEND_ORIGINS`,
   `FRONTEND_URL`, `BACKEND_BASE_URL`, and optionally the Google keys).
4. Deploy. Health check hits `/api/health`.

> The persistent `disk:` requires a **paid** instance (Starter+). To stay on the
> **free** tier, delete the `disk:` block and use managed Postgres instead (see
> the Postgres note below).

### Option C — Railway

1. **New Project → Deploy from GitHub repo**, set the service **Root Directory**
   to `backend` (it auto-builds the `Dockerfile`).
2. Add a **Volume** mounted at `/data`.
3. Add variables: `SECRET_KEY`, `DATABASE_URL=sqlite:////data/portfolio.sqlite3`,
   `FRONTEND_ORIGINS`, `FRONTEND_URL`, `BACKEND_BASE_URL`, and optionally Google keys.
4. Railway injects `PORT` automatically; the Dockerfile already honors it.

### Backend environment variables (all hosts)

| Variable | Example | Notes |
|----------|---------|-------|
| `SECRET_KEY` | long random string | JWT signing key |
| `DATABASE_URL` | `sqlite:////data/portfolio.sqlite3` | volume path, or a Postgres URL |
| `FRONTEND_ORIGINS` | `https://your-app.vercel.app` | comma-separated, **no trailing slash** |
| `FRONTEND_URL` | `https://your-app.vercel.app` | post-Google-login redirect target |
| `BACKEND_BASE_URL` | `https://xirr-backend.onrender.com` | this backend's public URL |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | *(optional)* | enables "Continue with Google" |

Verify: open `https://<backend-url>/api/health` → `{"status":"ok",...}`.

---

## 2. Frontend (Vercel Hobby)

Config lives in [`frontend/vercel.json`](frontend/vercel.json).

1. Vercel → **Add New… → Project** → import the repo.
2. Set **Root Directory** = `frontend` (framework auto-detects as Vite).
3. Add an **Environment Variable**:
   - `VITE_BACKEND_URL` = your backend URL, e.g. `https://xirr-backend.onrender.com`
     (Production **and** Preview; no trailing slash).
4. Deploy. `vercel.json` handles the SPA fallback so client routes like
   `/holdings` work on refresh.

> `VITE_*` vars are baked in at **build time** — after changing `VITE_BACKEND_URL`
> you must **redeploy** the frontend.

---

## 3. Wire the two together

1. Copy the Vercel domain (e.g. `https://your-app.vercel.app`).
2. On the backend host, set `FRONTEND_ORIGINS` and `FRONTEND_URL` to that domain
   and redeploy/restart.
3. (If using Google login) In Google Cloud Console add the authorized redirect
   URI: `https://<backend-url>/api/auth/google/callback`.

Then open the Vercel URL, register, and confirm uploads / analytics work.

---

## Using Postgres instead of SQLite

For a fully free Render setup (or any managed Postgres such as Neon/Supabase):

1. The `psycopg` (v3) driver is already in `backend/requirements.txt`.
2. Set `DATABASE_URL` to the provider's connection string as-is, e.g.
   `postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require`.
   Plain `postgres://` / `postgresql://` URLs are auto-adapted to psycopg v3 at
   startup, so you don't need to hand-edit the driver in the URL.

SQLAlchemy handles the rest; the schema is created automatically on startup.

## Troubleshooting

- **CORS errors in the browser console** → `FRONTEND_ORIGINS` doesn't exactly
  match the Vercel origin (scheme + host, no trailing slash). Redeploy the backend.
- **Data resets after redeploy** → the volume/disk isn't mounted, or
  `DATABASE_URL` doesn't point at the mount path.
- **Google login loops or 400** → `BACKEND_BASE_URL`/`FRONTEND_URL` are wrong, or
  the Google authorized redirect URI doesn't match `<BACKEND_BASE_URL>/api/auth/google/callback`.
- **Frontend still calls localhost** → `VITE_BACKEND_URL` wasn't set at build time;
  set it in Vercel and redeploy.
