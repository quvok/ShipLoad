# Domain model (initial)

## Vessel
Identity and particulars: IMO/official identifiers where appropriate, name, vessel type, dimensions, reference coordinate system, datum definitions, approved document set and active reviewed data revision.

## SourceDocument
Original immutable file, checksum, media type, upload time, uploader, extraction status and document revision. Keep original bytes separate from extracted content.

## ExtractedCandidate
Candidate field/table value, raw text, normalized candidate, unit, document/page/table/cell location, parser version, confidence and review status. Candidate data is never calculation input until reviewed.

## VesselDataRevision
A versioned snapshot containing accepted lightship particulars, hydrostatic data, tank data, capacity/geometry data, operating limits and applicable criteria. Each record links to its source and reviewer.

## Tank
Tank identity, type, capacity, geometry/table reference, permeability where applicable, sounding/ullage conventions, liquid density assumptions and longitudinal/transverse/vertical reference definitions.

## LoadingCondition
Named condition and timestamp. Contains lightship reference plus individually identified weights: cargo, ballast, fuel, diesel, fresh water, lubricants, stores, crew/passengers and other variable weights. Each item records mass, position or approved tank/table reference, density where relevant and source.

## CalculationRun
Immutable snapshot of condition + vessel revision + engine version + criteria version. Stores outputs, warnings, rejected checks, interpolation metadata, status and audit trail.

## Units and coordinate conventions
Use SI internally (kg, m, kg/m³, degrees). Define vessel axes and origin per vessel; never assume that positive x, y or z has the same meaning across ships. Every imported coordinate must be mapped to the vessel's approved datum before use.

## Important distinctions
- Displacement mass and weight force are not interchangeable.
- Draft readings, moulded draft, keel corrections, water density and trim reference need explicit conventions.
- Tank mass depends on approved capacity/sounding data and liquid density; tank free-surface moments depend on geometry and filling state.
- Lightship KG/LCG/TCG and constants must be sourced from approved particulars, not inferred from general dimensions.
