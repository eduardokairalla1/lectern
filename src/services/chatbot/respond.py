"""
Non-streaming chatbot orchestration.
"""

# --- IMPORTS ---
from src.services.chatbot.persistence import schedule_cache_hit_persistence
from src.services.chatbot.persistence import schedule_memory_update
from src.services.chatbot.persistence import schedule_persistence
from src.services.chatbot.pipeline import build_initial_state
from src.services.chatbot.pipeline import elapsed_ms
from src.services.chatbot.pipeline import prepare_state
from src.services.chatbot.pipeline import resolve_request_context
from src.services.chatbot.steps.answer import answer
from src.services.chatbot.types import ChatbotResult
from src.services.chatbot.types import ChatMessage
from uuid import uuid4

import logging
import time


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
async def respond(
    chat_message: ChatMessage,
    request_ip: str | None,
    user_agent: str | None,
) -> ChatbotResult:
    """
    Processes a chatbot request and returns the assistant's response.

    :param chat_message: The resolved chat message input.
    :param request_ip: Resolved client IP, for session/analytics tracking.
    :param user_agent: Client user agent, for session/analytics tracking.

    :return: Dict with the assistant response, ready to be serialized.
    """
    # start timing
    start_time = time.time()

    # log process start
    logger.info(
        f'Chatbot request started. Session: {chat_message.session_id}, '
        f'Type: {chat_message.message_type}'
    )

    # resolve the request context
    message, recent_interactions, cached_response = \
        await resolve_request_context(chat_message)

    # have a cached response: return it immediately and schedule memory update
    if cached_response:

        # update conversation memory
        await schedule_memory_update(
            chat_message.session_id, message, cached_response['response']
        )

        # schedule persistence of the cache hit
        exchange_id = str(uuid4())
        schedule_cache_hit_persistence(
            exchange_id=exchange_id,
            session_id=chat_message.session_id,
            user_message=message,
            cached_response=cached_response,
            request_ip=request_ip,
            user_agent=user_agent,
        )

        # log cache hit and return cached response
        logger.info(
            f'Chatbot request completed (CACHE HIT). '
            f'Session: {chat_message.session_id}, '
            f'Duration: {elapsed_ms(start_time)}ms'
        )
        return {'response': cached_response['response'],
                'exchangeId': exchange_id}

    # build the initial state and preprare it
    state = build_initial_state(
        chat_message.session_id, message, recent_interactions
    )
    state = await prepare_state(state)

    # run the answer step
    state = await answer(state)

    # calculate total duration
    total_duration_ms = elapsed_ms(start_time)
    logger.info(
        f'Chatbot request completed. Session: {chat_message.session_id}, '
        f'Exchange: {state["exchangeId"]}, Duration: {total_duration_ms}ms'
    )

    # run execution persistence
    await schedule_persistence(
        request_ip=request_ip,
        user_agent=user_agent,
        session_id=chat_message.session_id,
        user_message=message,
        response_state=state,
        total_duration_ms=total_duration_ms,
    )

    # get the final response from the state
    response = state['response']

    # NOTE: this should never be None here (the answer step always sets it).
    #       The assert exists purely to narrow the type for mypy below would
    #       otherwise be flagged as a possible None access.
    assert response is not None

    # return the final response
    return {
        'response': response.response,
        'exchangeId': state['exchangeId'],
    }
