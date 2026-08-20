"""
Chabot persistence functions
"""

# --- IMPORTS ---
from src.config import config
from src.services.chatbot import memory
from src.services.chatbot.types import Execution
from src.tasks.chatbot import save_memory
from src.types.stats import ExecutionStats
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


