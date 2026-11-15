# Architecture

## System boundaries

1. Web client — vessel workspace, document review, loading-condition editor, result visualizations and reports.
2. API — authentication/authorization, vessel and document lifecycle, calculation orchestration.
3. Document ingestion — file validation, text/table extraction, OCR where required, candidate field mapping and provenance.
4. Canonical vessel data — reviewed particulars, hydrostatic tables, tank calibration tables, lightship data, limits and source revisions.
5. Calculation engine — deterministic numerical services. No OCR, LLM or UI dependencies.
6. Validation harness — golden reference cases, property tests, regression tests and calculation audit records.

## Data flow

Original file -> extraction candidates -> human review -> immutable approved data revision -> loading condition -> calculation run -> validation/status -> report.

A calculation run must reference exact versions of the vessel data, loading inputs, calculation engine and criteria configuration. Editing a vessel profile creates a new revision; it must not silently rewrite historical runs.

## Initial stack

- Frontend: React, TypeScript, Vite.
- Backend: Python 3.12+, FastAPI, Pydantic.
- Persistence: PostgreSQL with SQLAlchemy/Alembic.
- Tests: pytest; frontend tests to be selected with the first UI scaffold.
- Deployment: containerized services behind HTTPS.

## Service contracts

- Document parser returns untrusted candidates plus page/table/cell provenance.
- Review service converts accepted candidates into versioned canonical records.
- Calculation service accepts only validated canonical data and a complete loading condition.
- Result service returns values, units, input completeness, warnings, limits checked and provenance.
- Report service renders a snapshot; it does not recalculate using mutable current data.

## Failure behavior

Unknown units, ambiguous tank identity, missing centres, out-of-range interpolation, conflicting source revisions, unsupported trim/heel assumptions and incomplete loading inputs must block the affected calculation or mark it explicitly incomplete. Never silently substitute zero or extrapolate.
