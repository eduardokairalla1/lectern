"""
Database engine factory.
"""

# --- IMPORTS ---
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine


# --- FACTORY ---
def create_database_engine(url: str) -> AsyncEngine:
    """
    Creates the async SQLAlchemy engine used for database connections.

    :param url: Database connection string (postgresql+psycopg://).

    :returns: Configured AsyncEngine instance.
    """
    return create_async_engine(
        url=url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
