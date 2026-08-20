"""
Caches a successful chatbot response.
"""

# --- IMPORTS ---
from src.services.chatbot import cache
from src.tasks.chatbot.config import RETRY_OPTIONS
from src.tasks.runner import run_async
from src.worker import celery_app


# --- CODE ---
@celery_app.task(name='chatbot.save_cache_response', **RETRY_OPTIONS)
def save_cache_response(
    query: str,
    response: str,
    answered: bool,
    category: str
) -> None:
    """
    Caches a successful response for future identical first messages.

    :param query: User's original query.
    :param response: Assistant's response.
    :param answered: Whether the question was answered.
    :param category: Response category.

    :returns: None.
    """
    run_async(
        cache.set_cached_response(
            query=query,
            response=response,
            answered=answered,
            category=category,
        )
    )
