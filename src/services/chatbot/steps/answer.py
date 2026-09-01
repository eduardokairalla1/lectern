"""
Generates final LLM response step.
"""

# --- IMPORTS ---
from src.clients.llms import STRUCTURED_ASSISTANT_LLM
from src.config import config
from src.services.chatbot.prompts import build_answer_prompt
from src.services.chatbot.types import Execution
from src.services.chatbot.types import State

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ----
async def answer(state: State) -> State:
    """
    Generates an answer for the user message based on the current state.

    :param state: The current state of the chatbot session.

    :return: The updated state with the generated llm response.
    """
    logger.debug(
        f'[Step: answer] Generating LLM response. '
        f'Exchange: {state["exchangeId"]}'
    )

    # build the prompt
    prompt = build_answer_prompt(
        message=state['message'],
        history=state['memoryText'],
        context=state['context'],
        language=state['language'],
    )

    # call the LLM
    try:
        response = await STRUCTURED_ASSISTANT_LLM.ainvoke(prompt)

    # error during LLM invocation: log and raise
    except Exception:
        logger.error(
            f'[Step: answer] LLM response generation failed. '
            f'Exchange: {state["exchangeId"]}',
            exc_info=True,
        )
        raise

    # update the state with the response and execution
    state['response'] = response['parsed']
    state['execution'].append(
        Execution.from_message(
            response['raw'], 'chatbot_answer', config.PRINCIPAL_MODEL
        )
    )

    logger.debug(
        f'[Step: answer] LLM response generated successfully. '
        f'Exchange: {state["exchangeId"]}'
    )

    # return updated state
    return state
