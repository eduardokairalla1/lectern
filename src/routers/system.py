"""
System endpoints.
"""

# --- IMPORTS ---
from fastapi import APIRouter
from fastapi import Depends
from src.dependencies.resources import get_health
from src.system import Health


# --- GLOBALS ---
router = APIRouter()


# --- CODE ---
@router.get('/health',
            summary='Liveness probe',
            response_model=Health)
def health_endpoint(health: Health = Depends(get_health)) -> Health:
    """
    Reports whether the service finished starting up.

    `OK` is set once startup completed and Redis answered a ping. The status
    reflects the process itself, not its dependencies at request time: a
    database that fails mid-request surfaces as a `503` on that request, not
    here. Always answers `200`; read the `status` field.
    """
    return health
