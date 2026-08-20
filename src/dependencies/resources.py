"""
Dependency providers for the per-app runtime state.
"""

# --- IMPORTS ---
from fastapi import Request
from src.system import Health
from src.system import Info


# --- CODE ---
def get_health(request: Request) -> Health:
    """
    Provides the runtime health object.

    :param request: FastAPI request object.

    :return: The application Health state.
    """
    return request.app.state.health


def get_info(request: Request) -> Info:
    """
    Provides the system information object.

    :param request: FastAPI request object.

    :return: The application Info metadata.
    """
    return request.app.state.info
