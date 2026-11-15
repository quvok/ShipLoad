from fastapi import FastAPI

from app.schemas.loading import LoadingConditionCreate

app = FastAPI(
    title="ShipLoad API",
    version="0.1.0",
    description=(
        "Development API for vessel data and loading-condition workflows. "
        "Not approved for operational loading or stability decisions."
    ),
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "shipload-api"}


@app.get("/api/v1/status", tags=["system"])
def status() -> dict[str, str]:
    return {
        "project": "ShipLoad",
        "stage": "foundation",
        "calculation_engine": "not_implemented",
        "operational_approval": "not_approved",
    }


@app.post("/api/v1/validation/loading-condition", tags=["validation"])
def validate_loading_condition(
    condition: LoadingConditionCreate,
) -> dict[str, object]:
    """Validate input structure only; this endpoint performs no naval calculations."""
    return {
        "status": "REVIEW_REQUIRED",
        "vessel_id": condition.vessel_id,
        "condition_name": condition.name,
        "vessel_data_revision": condition.vessel_data_revision,
        "item_count": len(condition.items),
        "message": (
            "Input structure is valid. Source documents and all technical values "
            "still require human verification. No displacement, trim or stability "
            "calculation has been performed."
        ),
    }
