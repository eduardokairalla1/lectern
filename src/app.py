"""
FastAPI application instance.
"""

# --- IMPORTS ---
from fastapi import FastAPI
from importlib.metadata import version
from src.config import config


# --- GLOBALS ---
_is_production = config.ENVIRONMENT.strip().lower() == 'production'

DESCRIPTION = """
A self-hostable, headless backend that turns a declared identity and a set of
documents into two things any client can consume: **structured identity** and
**grounded conversation**, in a persona you configure.

The subject can be a person, a company or a product — it is whoever the
deployment's identity file declares. Nothing about it is baked into the code.

### Getting started

Every `/chatbot` route requires the `x-api-key` header.

A conversation is identified by a `sessionId` you generate on the client and
reuse across messages — it is what ties the memory (summary plus recent
interactions) together. Use the same value for as long as the conversation
lasts, and a fresh one when it starts over.

### Errors

Failures share one envelope, `{"error": "<slug>", "message": "<text>"}`.
Branch on the slug: it is stable, while messages are free to change.
"""

APP_VERSION = version('lectern')


# --- CODE ---
app = FastAPI(
    title='Lectern',
    description=DESCRIPTION,
    summary='Headless backend for a grounded AI that speaks for one entity.',
    version=APP_VERSION,
    docs_url=None if _is_production else f'{config.API_PREFIX}/docs',
    redoc_url=None if _is_production else f'{config.API_PREFIX}/redoc',
    openapi_url=None if _is_production else f'{config.API_PREFIX}/openapi.json',
)
