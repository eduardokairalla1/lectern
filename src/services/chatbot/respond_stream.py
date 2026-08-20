"""
Streaming chatbot orchestration (SSE).
"""

# --- IMPORTS ---
from collections.abc import AsyncGenerator
from src.services.chatbot.events import classify_stream_error
from src.services.chatbot.events import done_event
from src.services.chatbot.events import error_event
from src.services.chatbot.events import format_sse
from src.services.chatbot.events import ready_event
from src.services.chatbot.events import sanitize_output
from src.services.chatbot.events import stream_end_event
from src.services.chatbot.events import token_event
from src.services.chatbot.persistence import schedule_cache_hit_persistence
from src.services.chatbot.persistence import schedule_memory_update
from src.services.chatbot.persistence import schedule_persistence
from src.services.chatbot.pipeline import build_initial_state
from src.services.chatbot.pipeline import elapsed_ms
from src.services.chatbot.pipeline import prepare_state
from src.services.chatbot.steps.stream_answer import stream_answer
from src.services.chatbot.types import CachedResponse
from src.services.chatbot.types import ChatMessage
from src.services.chatbot.types import State
from src.services.chatbot.types import StreamEvent
from uuid import uuid4

import asyncio
import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)

# max total time for stream endpoint
MAX_STREAM_TOTAL_DURATION_SECONDS = 90


# --- CODE ---
async def _execute_pipeline_streaming(
    state: State,
) -> AsyncGenerator[StreamEvent, None]:
    """
    Execute the pipeline with streaming on the answer step.

    :param state: The current state of the chatbot session.

    :return: An async generator yielding events to be sent to the client.
    """
    logger.info(
        f'[Streaming] Starting pipeline execution. '
        f'Session: {state["sessionId"]}'
    )

    # prepare the state (load memory, etc.)
    state = await prepare_state(state)

    # execute the answer step with streaming
    async for event in stream_answer(state):
        yield event

    # get the final response from the state
    response = state['response']

    # streaming ended with an error: skip stats/cache
    if response is None:
        return

    logger.info(
        f'[Streaming] Pipeline execution complete. '
        f'Session: {state["sessionId"]}'
    )

    # yield the final done event with the response metadata
    yield done_event(
        response.answered,
        response.category,
        state['exchangeId'],
    )


async def _generate(
    chat_message: ChatMessage,
    request_ip: str | None,
    user_agent: str | None,
    message: str,
    recent_interactions: list,
    cached_response: CachedResponse | None,
    start_time: float,
) -> AsyncGenerator[str, None]:
    """
    Generate the streaming response, handling cached responses and errors.

    :param chat_message: The resolved chat message input.
    :param request_ip: Resolved client IP, for session/analytics tracking.
    :param user_agent: Client user agent, for session/analytics tracking.
    :param message: The resolved user message (after transcription, if any).
    :param recent_interactions: The recent interactions for the session.
    :param cached_response: The cached response, if any.
    :param start_time: The timestamp when the request started.

    :return: An async generator yielding SSE frames.
    """
    # yield the ready event and then stream the response
    try:
        yield format_sse(ready_event(chat_message.session_id))

        # start timeout
        async with asyncio.timeout(MAX_STREAM_TOTAL_DURATION_SECONDS):

            # have a cached response: stream it and return immediately.
            if cached_response:
                async for frame in _stream_cached_response(chat_message,
                                                           message,
                                                           cached_response,
                                                           request_ip,
                                                           user_agent):
                    yield frame
                return

            # build the initial state
            state = build_initial_state(
                chat_message.session_id, message, recent_interactions
            )

            # execute the pipeline with streaming
            async for event in _execute_pipeline_streaming(state):
                yield format_sse(event)

            # stream errored: skip stats/cache
            if state['response'] is None:
                logger.warning(
                    f'Chatbot stream ended with error; skipping '
                    f'stats/cache. Session: {chat_message.session_id}'
                )
                return

            # calculate duration
            total_duration_ms = elapsed_ms(start_time)
            logger.info(
                f'Chatbot stream completed. '
                f'Session: {chat_message.session_id}, '
                f'Exchange: {state["exchangeId"]}, '
                f'Duration: {total_duration_ms}ms'
            )

            # run persistence of the session and response
            await schedule_persistence(
                request_ip=request_ip,
                user_agent=user_agent,
                session_id=chat_message.session_id,
                user_message=message,
                response_state=state,
                total_duration_ms=total_duration_ms,
            )

    # errors occurred during streaming: classify and yield an error event
    except Exception as e:
        code, msg = classify_stream_error(e)
        logger.error(
            f'Chatbot stream error ({code}). '
            f'Session: {chat_message.session_id}, Error: {str(e)}',
            exc_info=True,
        )

        # yield the error event to the client
        yield format_sse(error_event(code, msg))


async def _stream_cached_response(
    chat_message: ChatMessage,
    message: str,
    cached_response: CachedResponse,
    request_ip: str | None,
    user_agent: str | None,
) -> AsyncGenerator[str, None]:
    """
    Stream a cached response in chunks to the client.

    :param chat_message: The resolved chat message input.
    :param message: The resolved user message (after transcription, if any).
    :param cached_response: The cached response to be streamed.
    :param request_ip: Resolved client IP, for session/analytics tracking.
    :param user_agent: Client user agent, for session/analytics tracking.

    :return: An async generator yielding SSE frames.
    """
    logger.info(
        f'Chatbot stream (CACHE HIT). Session: {chat_message.session_id}'
    )

    # get the cached response text and sanitize it for streaming
    response_text = cached_response['response']
    sanitized_response = sanitize_output(response_text)

    # define the chunk size
    chunk_size = 10

    # iterate over the sanitized response in chunks
    for i in range(0, len(sanitized_response), chunk_size):

        # yield each chunk as an SSE token event
        yield format_sse(token_event(sanitized_response[i : i + chunk_size]))

    # streaming complete: yield the stream end event
    yield format_sse(stream_end_event())

    # update conversation memory for the cached response
    await schedule_memory_update(
        chat_message.session_id, message, response_text
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
    yield format_sse(
        done_event(
            cached_response.get('answered', True),
            cached_response.get('category', 'general'),
            exchange_id,
        )
    )


