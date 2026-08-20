"""
Chabot persistence functions
"""

# --- IMPORTS ---
from src.config import config
from src.services.chatbot.types import Execution
from src.types.stats import ExecutionStats

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


