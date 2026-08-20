"""
Conversation summary memory.
"""

# --- IMPORTS ---

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CONSTANTS ---
TTL_SECONDS = 30 * 60
MAX_SUMMARY_CHARS = 2000
MAX_RECENT_INTERACTIONS = 2


# --- CODE ---
def _summary_key(session_id: str) -> str:
    """
    Redis key holding the conversation summary.

    :param session_id: Conversation identifier.

    :return: Redis key for the summary.
    """
    return f'memory:{session_id}'


def _recent_key(session_id: str) -> str:
    """
    Redis key holding the recent raw interactions.

    :param session_id: Conversation identifier.

    :return: Redis key for the recent interactions.
    """
    return f'memory:{session_id}:recent'


def _format(summary: str, recent: list[tuple[str, str]]) -> str:
    """
    Formats the conversation summary with recent interactions.

    :param summary: The conversation summary.
    :param recent: Recent interactions, as a list of (user_input, response).

    :return: The formatted conversation summary with recent interactions.
    """
    # no recent interactions: return the summary as-is
    if not recent:
        return summary

    # format the recent interactions as a list of lines
    lines = ['Recent interactions:']

    # append each recent interaction as a numbered pair of lines
    for i, (inp, resp) in enumerate(recent, 1):
        lines.append(f'Question {i}: {inp}')
        lines.append(f'AI Response {i}: {resp}')

    # return the summary followed by the recent interactions
    return f'{summary}\n\n' + '\n'.join(lines)


