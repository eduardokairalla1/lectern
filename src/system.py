"""
Application runtime state.
"""

# --- IMPORTS ---
from pydantic import BaseModel
from typing import Any
from typing import Literal


# --- CODE ---
class Health(BaseModel):
    """
    Liveness state of the process.
    """

    status: Literal['OK', 'WARNING', 'FAILURE', 'UNKNOWN'] = 'UNKNOWN'


class Info(BaseModel):
    """
    Metadata of the running build.
    """
    name: str
    description: str
    version: str
    extra: dict[str, Any]
