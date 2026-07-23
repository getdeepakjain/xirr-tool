# Portfolio XIRR Tracker

A full-stack personal investment tracker for **Mutual Funds, Stocks, FD, Bonds, NPS, PF,
Crypto, Insurance Policies and Gratuity**. Import your holdings from a multi-tab Excel
workbook (only *new* rows are added on re-upload), manage them manually, and get
**XIRR** (money-weighted annualised returns) per script, per asset class and for the
whole portfolio — plus automated insights on what's doing well and what needs attention.

<p align="center">
  <em>FastAPI + SQLite backend &nbsp;·&nbsp; React + Vite + TypeScript frontend</em>
</p>

## Features

- **Profiles** — create / update / delete multiple portfolios (e.g. self, spouse, kids).
- **Excel import** — upload the `Upload Format.xlsx` workbook. Each tab (Stocks, FD, PF,
  Gratuity, NPS Tier I/II, MF, Policies, Bonds, Crypto) is parsed into holdings and
  transactions. Re-uploading only imports **new** transactions (content-hash dedup).
- **Manual CRUD** — add / edit / delete holdings and individual transactions for every
  asset class.
- **XIRR everywhere** — per holding, per asset class, and for the entire portfolio, using a
  cash-flow model (investments are outflows, current market value is the terminal inflow).
- **Insights** — top performers, laggards below inflation, negative-return holdings,
  concentration risk, low diversification, stop-loss breaches, and overall health.
- **Auth** — email/password (JWT) **or** "Continue with Google" (OAuth 2.0).
- **Dashboard** — allocation pie, XIRR-by-class bar chart, and summary tables.
- **Sortable holdings** — click any column header on the Holdings page to sort.
- **CSV export** — download holdings and transactions as CSV from the Holdings page.
- **Market price refresh** — one click pulls the latest MF NAV (AMFI), stock price
  (Yahoo Finance) and crypto price (CoinGecko, in INR) for unit-priced holdings.
- **Automated tests** — a `pytest` suite covering XIRR, valuation, the Excel importer,
  price matching, and the REST API.

## Tech stack

| Layer     | Tech |
|-----------|------|
| Backend   | Python, FastAPI, SQLAlchemy, SQLite, openpyxl, pyxirr, python-jose, Authlib |
| Frontend  | React 18, TypeScript, Vite, React Router, Recharts, Axios |
| Auth      | JWT access tokens + optional Google OAuth |

## Project layout

```
xirr-tool/
├─ backend/
│  ├─ app/
│  │  ├─ main.py            # FastAPI app + router wiring
│  │  ├─ models.py          # User / Profile / Holding / Transaction
│  │  ├─ importer.py        # per-tab Excel parsers + dedup
│  │  ├─ xirr.py            # XIRR solver (pyxirr + pure-python fallback)
│  │  ├─ valuation.py       # invested / current value / cash flows
│  │  ├─ insights.py        # rule-based recommendations
│  │  ├─ prices.py          # market price refresh (AMFI / Yahoo / CoinGecko)
│  │  └─ routers/           # auth, profiles, holdings, transactions, uploads,
│  │                        #   analytics, exports (CSV), market (price refresh)
│  ├─ tests/                # pytest suite (offline)
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/
│  ├─ src/                  # React app (pages, components, api client)
│  ├─ package.json
│  └─ .env.example
├─ Upload Format.xlsx       # sample import workbook
├─ LICENSE
└─ README.md
```

## Getting started

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env          # (macOS/Linux: cp .env.example .env)
# edit .env and set a strong SECRET_KEY

uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`). The SQLite
database is created automatically at `backend/data/portfolio.sqlite3`.

### 2. Frontend

```bash
cd frontend
npm install
copy .env.example .env          # optional; defaults work for local dev
npm run dev
```

Open `http://localhost:5173`, create an account, then go to **Upload Excel** and drop in
`Upload Format.xlsx`.

### Running the tests

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest      # macOS/Linux: python -m pytest
```

The suite uses an isolated throwaway SQLite database and stubs out all network calls, so it
runs fully offline.

### 3. (Optional) Google login

1. In [Google Cloud Console](https://console.cloud.google.com/apis/credentials) create an
   **OAuth 2.0 Client ID** (Web application).
2. Add authorized redirect URI: `http://localhost:8000/api/auth/google/callback`.
3. Put `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `backend/.env` and restart the API.
   The "Continue with Google" button appears automatically.

## How XIRR is computed

Each holding produces a list of dated cash flows:

- every **buy** → negative amount on its date,
- every **sell / dividend / cashback** → positive amount on its date,
- the **current market value** → positive amount dated today.

XIRR is the annualised rate that makes the net present value of those flows zero. Unit-priced
assets (MF, Stocks, NPS, Crypto) value as `units × latest price`; the rest (FD, PF, Gratuity,
Bonds, Policies) use an explicit current value taken from the Excel or entered manually.

## Notes

- The bundled `Upload Format.xlsx` is a real-world style template; many columns are formulas.
  The importer reads the raw inputs it needs (name, date, amount, units/price, latest value)
  and recomputes returns itself.
- `backend/data/` and `.env` files are git-ignored — your financial data never leaves your
  machine.

## License

MIT — see [LICENSE](LICENSE).
