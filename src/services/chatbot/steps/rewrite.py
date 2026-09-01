"""
Query rewriting step.
"""

# --- IMPORTS ---
from src.clients.llms import STRUCTURED_REWRITE_MODEL
from src.config import config
from src.services.chatbot.prompts import build_rewrite_prompt
from src.services.chatbot.types import Execution
from src.services.chatbot.types import State

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
async def rewrite_query(state: State) -> State:
    """
    Rewrite the user query using the LLM.

    :param state: The current state of the chatbot session.

    :return: The updated state with the rewritten query.
    """
    logger.debug(
        f'[Step: rewrite_query] Rewriting query. '
        f'Exchange: {state["exchangeId"]}'
    )

    # get the message and recent interactions from the state
    message = state['message']
    recentInteractions = state['recentInteractions']

    # no recent interactions: use original message
    if not recentInteractions:
        state['rewrittenQuery'] = message
        logger.debug(
            f'[Step: rewrite_query] No context, using original query. '
            f'Exchange: {state["exchangeId"]}'
        )
        return state

    # build the context string from recent interactions
    contextLines = []
    for inp, resp in recentInteractions:
        contextLines.append(f'Question: {inp}')
        contextLines.append(f'Answer: {resp}')
    contextStr = '\n'.join(contextLines)

    # build the prompt for the rewrite model
    formattedPrompt = build_rewrite_prompt(
        query=message,
        context=contextStr
    )

    # call the rewrite model with a timeout
    try:
        response = await STRUCTURED_REWRITE_MODEL.ainvoke(formattedPrompt)

    # model call failed: keep the original query and carry on
    except Exception as e:
        logger.warning(
            f'[Step: rewrite_query] Failed to rewrite, using original. '
            f'Exchange: {state["exchangeId"]}, Error: {str(e)}'
        )
        state['rewrittenQuery'] = message
        return state

    # get the rewritten query and the detected language from the response
    parsed = response['parsed']

    # parsing failed: keep the original query and carry on
    if parsed is None:
        logger.warning(
            f'[Step: rewrite_query] Unparsed rewrite, using original. '
            f'Exchange: {state["exchangeId"]}, '
            f'Error: {response.get("parsing_error")}'
        )
        state['rewrittenQuery'] = message
        return state

    # get the rewritten query, defaulting to the original message if empty
    rewrittenQuery = parsed.query.strip() or message

    # append the rewrite execution to the state
    state['execution'].append(
        Execution.from_message(
            response['raw'],
            'query_rewrite',
            config.REWRITE_MODEL
        )
    )
    state['rewrittenQuery'] = rewrittenQuery

    # set the detected language in the state, stripping whitespace
    state['language'] = parsed.language.strip()

    logger.debug(
        f'[Step: rewrite_query] Query rewritten '
        f'({len(message)} -> {len(rewrittenQuery)} chars). '
        f'Exchange: {state["exchangeId"]}'
    )

    return state
