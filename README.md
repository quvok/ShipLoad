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

## Planned architecture

- `frontend/`: React + TypeScript browser application.
- `backend/`: Python + FastAPI API and calculation services.
- `docs/`: engineering decisions, domain model, validation and safety requirements.
- PostgreSQL: vessel profiles, source documents, reviewed hydrostatic/tank data and loading conditions.
- Object storage: original documents and generated reports.

The calculation engine is deliberately separated from document parsing and the user interface. OCR/LLM extraction may propose data, but it must never silently become authoritative calculation input.

## Development status

The repository is being initialized. No vessel-specific data, approved calculation model, or validated operational calculation is included yet.

## Development principles

1. SI units internally; conversions only at input/output boundaries.
2. Every value carries a unit, source and review state where applicable.
3. No extrapolation beyond approved table ranges without an explicit, validated method.
4. Missing or inconsistent inputs produce a blocked/incomplete result, not a plausible-looking number.
5. All calculations are deterministic and covered by tests using independently verified reference cases.
6. Regulatory criteria and applicability must be explicitly configured for the vessel; no universal pass/fail shortcut.
7. Reports distinguish calculated, imported, assumed and user-entered values.

## Planned local development

Backend and frontend setup instructions will be added with their first runnable application scaffolds.
