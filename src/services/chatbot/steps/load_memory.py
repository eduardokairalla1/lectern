"""
Session memory (summary).
"""

# --- IMPORTS ---
from src.errors.backend_error import BackendError
from src.errors.processing_error import ProcessingError
from src.services.chatbot import memory as memory_service
from src.services.chatbot.types import State

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
async def load_memory(state: State) -> State:
    """
    Loads the conversation memory (summary) and returns.

    :param state: The current state of the chatbot session.

    :return: The updated state, with the 'memoryText' field set to the
             loaded conversation history.
    """
    # load the conversation memory
    try:
        logger.debug(
            f'[Step: load_memory] Loading conversation memory. '
            f'Exchange: {state["exchangeId"]}'
        )
        state['memoryText'] = await memory_service.load_memory(
            state['sessionId'],
            state['recentInteractions'],
        )

        # return the results
        return state

    # BackendError: propagate the error to the caller
    except BackendError:
        raise

    # load memory summary error: raise a 500 error
    except Exception as e:
        logger.error(
            f'[Step: load_memory] Failed to load memory. '
            f'Session: {state["sessionId"]}, Error: {str(e)}',
            exc_info=True,
        )
        raise ProcessingError({'error': str(e)}) from e
