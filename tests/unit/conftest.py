"""
Shared test fixtures.
"""

# --- IMPORTS ---
import pytest


# --- ASYNC BACKEND ---
@pytest.fixture(scope='session')
def anyio_backend() -> str:
    """Run @pytest.mark.anyio tests on asyncio only (trio not installed)."""
    return 'asyncio'
