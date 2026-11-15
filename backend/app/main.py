from fastapi import FastAPI

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
