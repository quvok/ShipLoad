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
- `backend/`: Python + FastAPI API and calculation services.
- `docs/`: architecture, domain model, validation and safety requirements.
- Planned persistence: PostgreSQL; planned object storage for original documents and generated reports.

The calculation engine is deliberately separated from document parsing and the user interface. OCR/LLM extraction may propose data, but it must never silently become authoritative calculation input.

## Current implementation

- Initial responsive web workspace dashboard.
- FastAPI health and development-status endpoints.
- Guarded linear table interpolation primitive that rejects extrapolation and malformed tables.
- Backend tests for API status and interpolation boundaries.
- GitHub Actions workflow for backend lint/tests and frontend production build.

Not implemented yet: vessel persistence, authentication, document upload/extraction, reviewed hydrostatic/tank data, loading-condition management, vessel-specific stability calculations, criteria evaluation and report generation. No vessel-specific data or validated operational calculation is included.

## Local development

### Backend

Requires Python 3.12+.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

API health: `http://127.0.0.1:8000/health`

Run tests and lint:

```bash
pytest -q
ruff check app tests
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
