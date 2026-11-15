# Safety and validation requirements

ShipLoad is a development tool until the calculation methods, vessel data and operational workflow have been independently verified and any required approval has been obtained.

## Non-negotiable controls

- No operational green/pass status from unreviewed extracted data.
- No invented default vessel particulars, hydrostatics, tank centres, limits or stability criteria.
- Preserve units, datum, sign convention and source for every input.
- Block calculations when required inputs are missing, ambiguous, stale or outside supported ranges.
- Display assumptions and warnings next to results, not only in logs.
- Keep immutable calculation snapshots and audit history.
- Clearly separate an illustrative estimate from a verified calculation.
- Do not represent a successful software test as proof of vessel safety.

## Validation gates

1. Requirements gate: identify vessel type, approved booklets, coordinate system, calculation method, applicable stability criteria and expected operating envelope.
2. Data gate: reconcile every imported table and constant against source documents; verify units, ranges, interpolation points and revision.
3. Numerical gate: compare against independently prepared reference calculations and, where available, the vessel's approved loading computer outputs.
4. Boundary gate: test table endpoints, interpolation boundaries, invalid inputs, tank partial-fill cases, density changes and unsupported extrapolation.
5. Integration gate: verify document revision -> loading condition -> result traceability and report reproducibility.
6. Operational gate: independent naval-architecture/marine engineering review and applicable flag/class/company approval before operational use.

## Test strategy

Use golden datasets with documented provenance and expected values/tolerances. Include regression tests, dimensional/unit tests, property-based tests and adversarial malformed-document tests. Test tolerances must be defined by the approved method and reference data, not chosen to make tests pass.

## Status vocabulary

- DRAFT: entered but not reviewed.
- REVIEW_REQUIRED: extracted/imported and awaiting review.
- APPROVED_DATA: reviewed against source documentation.
- INCOMPLETE: calculation cannot be completed.
- ESTIMATE_ONLY: output is not validated for operational use.
- VALIDATED_TEST_CASE: software result matches a controlled reference case; this is not vessel approval.
- OPERATIONAL_APPROVAL_REQUIRED: required external review/approval is outstanding.

Never use a single generic green badge to imply vessel-wide compliance.
