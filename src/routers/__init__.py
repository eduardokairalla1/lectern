"""
HTTP routers.
"""

# --- IMPORTS ---
from fastapi import APIRouter
from fastapi import FastAPI
from src.config import config
from src.routers import chatbot
from src.routers import system
from src.routers import whoami


# --- CODE ---
def mount(app: FastAPI) -> None:
    """
    I mount all routers on application.

    :param app: main app router

    :returns: nothing
    """
    api = APIRouter(prefix=config.API_PREFIX)

    api.include_router(system.router, tags=['system'], prefix='/system')
    api.include_router(chatbot.router, tags=['chatbot'], prefix='/chatbot')
    api.include_router(whoami.router, tags=['whoami'])

    app.include_router(api)
