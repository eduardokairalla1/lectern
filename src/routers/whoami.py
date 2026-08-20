"""
Whoami endpoint.
"""

# --- IMPORTS ---
from fastapi import APIRouter
from src.identity import Subject
from src.identity import get_identity


# --- GLOBALS ---
router = APIRouter()


# --- CODE ---
@router.get('/whoami',
            summary='Public profile',
            response_model=Subject)
def whoami_endpoint() -> Subject:
    """
    Returns the public profile of the subject this instance speaks for.

    Open endpoint: no API key, and readable from any origin, so it can be
    fetched by tools and agents crawling the site. The payload comes from the
    deployment's identity file: `name` is always present, and every other
    field is whatever that file declares.
    """
    return get_identity().identity
