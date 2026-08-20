"""
The subject this instance speaks for.
"""

# --- IMPORTS ---
from pydantic import BaseModel
from pydantic import ConfigDict


# --- CODE ---
class Subject(BaseModel):
    """
    The public profile served by GET /whoami.
    """
    model_config = ConfigDict(extra='allow')

    name: str
