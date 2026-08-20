"""
Shared chatbot pipeline.

Single source of truth for the ordered pre-answer steps
(load memory -> rewrite query -> retrieve context).

The answer step differs between paths (structured, one-shot answer vs. token
streaming), so it stays in each orchestrator; everything before it is shared.
"""

# --- IMPORTS ---
from src.services.chatbot import cache
from src.services.chatbot import memory
from src.services.chatbot.message import resolve_message
from src.services.chatbot.types import CachedResponse
from src.services.chatbot.types import ChatMessage

import asyncio
import time


# --- CODE ---
def elapsed_ms(start_time: float) -> int:
    """
    Elapsed time since the request started, in milliseconds.

    :param start_time: The timestamp when the request started.

    :return: Elapsed time in milliseconds.
    """
    return int((time.time() - start_time) * 1000)


async def resolve_request_context(
    chat_message: ChatMessage,
) -> tuple[str, list[tuple[str, str]], CachedResponse | None]:
    """
    Resolves the user message, fetches recent interactions and checks for a
    cached response (only when there is no prior context).

    :param chat_message: The resolved chat message input.

    :return: Tuple of (message, recent_interactions, cached_response).
        cached_response is None on a cache miss or when there is prior
        context.
    """
    # resolve the message and fetch recent interactions concurrently
    message, recent_interactions = await asyncio.gather(
        resolve_message(chat_message),
        memory.get_recent_interactions(chat_message.session_id),
    )

    # initialize cached response
    cached_response = None

    # no recent interactions: check for a cached response
    if not recent_interactions:
        cached_response = await cache.get_cached_response(message)

    # return the resolved message, recent interactions and cached response
    return message, recent_interactions, cached_response


