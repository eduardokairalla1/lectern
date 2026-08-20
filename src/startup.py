"""
Startup and shutdown event handlers.
"""

# --- IMPORTS ---
from fastapi import FastAPI
from src.resources import close_resources
from src.resources import get_resources
from src.system import Health
from src.system import Info

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
async def on_startup(app: FastAPI) -> None:
    """
    Initialize the service on startup.
    """
    # create the shared resources and expose them to the request handlers
    resources = get_resources()
    app.state.resources = resources

    # initialize health and info
    app.state.health = Health()
    app.state.info = Info(
        name=app.title,
        description=app.description,
        version=app.version,
        extra={},
    )

    # test redis connection
    await resources.redis_client.ping()

    # set app health as OK
    app.state.health.status = 'OK'

    # log service start
    logger.info('Service started (status=%s)', app.state.health.status)


async def on_shutdown(app: FastAPI) -> None:
    """
    Run on service shutdown.
    """
    # log service shutdown
    logger.info('Service shutting down')

    # close every client and dispose the database engine
    await close_resources()
