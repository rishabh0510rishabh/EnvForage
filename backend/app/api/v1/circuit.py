
# --- Circuit Breaker State API ---
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/circuit-breakers", tags=["Admin"])

# Simulated global state of circuit breakers registered in the app
# Keys are integration names (e.g., 'sendgrid', 'payment_gateway')
_CIRCUIT_REGISTRY: dict[str, dict[str, Any]] = {
    "payment_gateway": {
        "state": "CLOSED",
        "failures": 0,
        "last_failure_at": None,
        "config": {"threshold": 5, "timeout": 30}
    },
    "notification_service": {
        "state": "OPEN",
        "failures": 12,
        "last_failure_at": "2024-01-01T12:00:00Z",
        "config": {"threshold": 10, "timeout": 60}
    }
}

class CircuitStateUpdate(BaseModel):
    override_state: str # "OPEN", "HALF_OPEN", "CLOSED"

@router.get("/")
async def list_circuit_breakers() -> list[dict[str, Any]]:
    """
    Admin endpoint returning the real-time topological health
    of all registered external dependencies and their circuit breakers.
    """
    payload = []
    for name, data in _CIRCUIT_REGISTRY.items():
        payload.append({
            "integration_name": name,
            **data
        })
    return payload

@router.get("/{integration_name}")
async def get_circuit_breaker(integration_name: str) -> dict[str, Any]:
    """Retrieve the exact state and failure history of a specific circuit."""
    if integration_name not in _CIRCUIT_REGISTRY:
        raise HTTPException(status_code=404, detail="Circuit breaker not found")
    return {"integration_name": integration_name, **_CIRCUIT_REGISTRY[integration_name]}

@router.post("/{integration_name}/override")
async def override_circuit_state(integration_name: str, payload: CircuitStateUpdate) -> dict[str, Any]:
    """
    Allows SREs to manually trip (OPEN) or heal (CLOSED) a circuit breaker
    during an active incident response, bypassing the automated thresholds.
    """
    if integration_name not in _CIRCUIT_REGISTRY:
        raise HTTPException(status_code=404, detail="Circuit breaker not found")

    valid_states = {"OPEN", "HALF_OPEN", "CLOSED"}
    if payload.override_state not in valid_states:
        raise HTTPException(status_code=400, detail=f"Invalid state. Must be one of {valid_states}")

    # In a real app, this would trigger an event in the actual CircuitBreaker object
    _CIRCUIT_REGISTRY[integration_name]["state"] = payload.override_state
    if payload.override_state == "CLOSED":
        _CIRCUIT_REGISTRY[integration_name]["failures"] = 0

    return {
        "message": f"Circuit {integration_name} forced to {payload.override_state}",
        "current_state": _CIRCUIT_REGISTRY[integration_name]
    }
