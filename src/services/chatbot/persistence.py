"""
Chabot persistence functions
"""

# --- IMPORTS ---
from src.config import config
from src.services.chatbot import memory
from src.services.chatbot.types import CachedResponse
from src.services.chatbot.types import Execution
from src.services.chatbot.types import State
from src.tasks.chatbot import save_cache_response
from src.tasks.chatbot import save_exchange_stats
from src.tasks.chatbot import save_feedback
from src.tasks.chatbot import save_memory
from src.types.stats import ExchangeStats
from src.types.stats import ExecutionStats
from src.types.stats import SessionStats
from src.utils.dispatch import dispatch_task

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
def _build_execution_stats(
    executions: list[Execution],
    total_duration_ms: int
) -> list[ExecutionStats]:
    """
    Build a list of execution stats dicts from the executions collected in
    state['execution'].

    :param executions: Executions collected in state['execution'].
    :param total_duration_ms: Total request duration in milliseconds.

    :return: List of execution stats dicts, in pipeline order.
    """
    # initialize stats
    stats: list[ExecutionStats] = []

    # interate over executions
    for execution in executions:

        # test if execution was answered
        is_answer = execution.execution_type == 'chatbot_answer'

        # append execution in stats list
        stats.append(
            {
                'execution_type': execution.execution_type,
                'llm_model': execution.llm_model,
                'embedding_model': (
                    config.EMBEDDING_MODEL if is_answer else None
                ),
                'input_tokens': execution.input_tokens,
                'output_tokens': execution.output_tokens,
                'total_tokens': execution.total_tokens,
                'total_duration_ms': (
                    total_duration_ms if is_answer else None
                ),
            }
        )

    return stats


def schedule_feedback(
    exchange_id: str,
    rating: str,
    comment: str | None = None
) -> None:
    """
    Enqueues the upsert of a visitor feedback.

    :param exchange_id: UUID (string) of the rated exchange.
    :param rating: Visitor rating: 'up' or 'down'.
    :param comment: Optional free-text comment.

    :returns: None.
    """
    dispatch_task(
        save_feedback,
        exchange_id=exchange_id,
        rating=rating,
        comment=comment,
    )


def schedule_cache_hit_persistence(
    exchange_id: str,
    session_id: str,
    user_message: str,
    cached_response: CachedResponse,
    request_ip: str | None,
    user_agent: str | None,
) -> None:
    """
    Persists an exchange that was answered from the response cache.

    :param exchange_id: Identifier generated for this exchange.
    :param session_id: Conversation identifier.
    :param user_message: Resolved user message.
    :param cached_response: The cached payload that answered it.
    :param request_ip: Resolved client IP, for session/analytics tracking.
    :param user_agent: Client user agent, for session/analytics tracking.

    :returns: None.
    """
    # build the session and exchange stats
    session_data: SessionStats = {
        'id': session_id,
        'request_ip': request_ip,
        'user_agent': user_agent,
    }

    exchange_data: ExchangeStats = {
        'id': exchange_id,
        'session_id': session_id,
        'user_message': user_message,
        'assistant_response': cached_response['response'],
        'was_answered_successfully': cached_response.get('answered', True),
        'topic_category': cached_response.get('category'),
        'request_ip': request_ip,
        'served_from_cache': True,
    }

    # dispatch the persistence tasks
    dispatch_task(
        save_exchange_stats,
        session_data=session_data,
        exchange_data=exchange_data,
        executions=[],
    )


async def schedule_memory_update(
    session_id: str, user_message: str, assistant_response: str
) -> None:
    """
    Updates the recent-interactions memory and enqueues the
    summary regeneration.

    :param session_id: Conversation identifier.
    :param user_message: Resolved user message.
    :param assistant_response: Assistant response to persist.

    :returns: None.
    """
    await memory.update_recent_interactions(
        session_id, user_message, assistant_response
    )

    dispatch_task(
        save_memory,
        session_id=session_id,
        user_message=user_message,
        assistant_response=assistant_response,
    )


async def schedule_persistence(
    request_ip: str | None,
    user_agent: str | None,
    session_id: str,
    user_message: str,
    response_state: State,
    total_duration_ms: int,
) -> None:
    """
    Enqueues the persistence of the session, exchange, and execution stats.

    :param request_ip: Resolved client IP, for session/analytics tracking.
    :param user_agent: Client user agent, for session/analytics tracking.
    :param session_id: Conversation identifier.
    :param user_message: Resolved user message.
    :param response_state: Final state after the pipeline ran.
    :param total_duration_ms: Total request duration in milliseconds.

    :returns: None.
    """
    # extract the response from the state
    result = response_state['response']

    # response is None: log an error and skip persistence
    if result is None:
        logger.error(
            '[Persistence] Missing response in state; skipping. '
            f'Session: {session_id}'
        )
        return

    # response was not correctly answered: log a warning
    if not result.answered:
        logger.warning(
            f'Unanswered question. Session: {session_id}, '
            f'Exchange: {response_state["exchangeId"]}'
        )

    # build the session
    session_data: SessionStats = {
        'id': session_id,
        'request_ip': request_ip,
        'user_agent': user_agent,
    }

    # build the exchange
    exchange_data: ExchangeStats = {
        'id': response_state['exchangeId'],
        'session_id': session_id,
        'user_message': user_message,
        'assistant_response': result.response,
        'rewritten_query': response_state.get('rewrittenQuery'),
        'retrieved_documents': response_state.get('retrievedDocuments', []),
        'memory_summary': response_state.get('memoryText'),
        'was_answered_successfully': result.answered,
        'topic_category': result.category,
        'request_ip': request_ip,
        'served_from_cache': False,
    }

    # dispatch the persistence tasks
    dispatch_task(
        save_exchange_stats,
        session_data=session_data,
        exchange_data=exchange_data,
        executions=_build_execution_stats(response_state.get('execution', []),
                                          total_duration_ms),
    )

    # dispatch the cache save task
    dispatch_task(
        save_cache_response,
        query=user_message,
        response=result.response,
        answered=result.answered,
        category=result.category,
    )

    # update the conversation memory
    await schedule_memory_update(session_id, user_message, result.response)
