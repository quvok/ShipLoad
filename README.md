# ShipLoad

Browser-based vessel loading, draft, trim and stability workspace.

> **Safety status: development only.** ShipLoad is not an approved loading instrument and must not be used to authorize loading, sailing, ballast operations or other safety-critical decisions. Results require independent verification against the vessel's approved stability information and applicable onboard procedures.

## Project goals

- Maintain a separate, versioned technical profile for each vessel.
- Import vessel documents and extract candidate data with traceable source references.
- Require human review of extracted particulars, tables, units and limits.
- Build reproducible loading conditions from lightship, deadweight items, tanks and cargo.
- Calculate displacement, centres of gravity, draft/trim, free-surface effects and stability outputs using vessel-specific approved data.
- Preserve calculation inputs, software version, data provenance and validation status in every report.

## Architecture

- `frontend/`: React + TypeScript + Vite browser application.
- `backend/`: Python + FastAPI API, SQLAlchemy persistence and calculation services.
- `backend/migrations/`: Alembic database migrations.
- `docs/`: architecture, domain model, validation and safety requirements.
- PostgreSQL stores structured vessel data; original documents and reports will use separate object storage.

The calculation engine is deliberately separated from document parsing and the user interface. OCR/LLM extraction may propose data, but it must never silently become authoritative calculation input.

## Current implementation

- Russian-language responsive web workspace dashboard.
- FastAPI health and development-status endpoints.
- PostgreSQL-ready vessel registry API: create, list and retrieve vessel profiles.
- SQLAlchemy model and Alembic initial migration for the vessel registry.
- Explicit database configuration; vessel API returns HTTP 503 when `DATABASE_URL` is not configured. It does not silently use an in-memory database.
- New vessel profiles are marked `DRAFT`; this is not an approval of technical particulars.
- Guarded linear table interpolation primitive that rejects extrapolation and malformed tables.
- Structural loading-condition input validation; it performs no naval calculations.
- Backend tests for API status, interpolation boundaries, loading schemas and vessel registry behavior.
- GitHub Actions workflow for backend lint/tests and frontend production build.

Not implemented yet: authentication, document upload/extraction, reviewed hydrostatic/tank data, loading-condition persistence, vessel-specific stability calculations, criteria evaluation and report generation. No vessel-specific data or validated operational calculation is included.

## Local development

### Backend

Requires Python 3.12+ and PostgreSQL.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

Set `DATABASE_URL` in the environment (or load it from your local environment manager), for example:

```text
postgresql+psycopg://shipload:change-me@localhost:5432/shipload
```

Create the database, then apply migrations:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

API health: `http://127.0.0.1:8000/health`

Vessel API:
- `POST /api/v1/vessels` — create a draft vessel profile.
- `GET /api/v1/vessels` — list vessel profiles.
- `GET /api/v1/vessels/{vessel_id}` — retrieve a vessel profile.

Run tests and lint:

```bash
pytest -q
ruff check app tests migrations
```

### Frontend

Requires Node.js 22+.

```bash
cd frontend
npm install
npm run dev
```

The Vite development server starts at `http://localhost:5173`.

## Development principles

1. SI units internally; conversions only at input/output boundaries.
2. Every value carries a unit, source and review state where applicable.
3. No extrapolation beyond approved table ranges without an explicit, validated method.
4. Missing or inconsistent inputs produce a blocked/incomplete result, not a plausible-looking number.
5. All calculations are deterministic and covered by tests using independently verified reference cases.
6. Regulatory criteria and applicability must be explicitly configured for the vessel; no universal pass/fail shortcut.
7. Reports distinguish calculated, imported, assumed and user-entered values.
8. A passing software test is not evidence that a vessel is safe or that the application is approved.

## Safety and validation

Read [Safety and Validation](docs/SAFETY_AND_VALIDATION.md) before implementing or interpreting calculation outputs. Operational use requires independent engineering verification and any applicable flag, class and company approval.