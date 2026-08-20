"""
Output parsers for the llms
"""

# --- IMPORTS ---
from pydantic import BaseModel
from pydantic import Field


# --- CODE ---
class ResponseOutputParser(BaseModel):
    """
    Output parser for the chatbot response
    """
    response: str = Field(
        ...,
        description=(
            'Final chatbot reply to the user, written in the SAME language as '
            "the user's latest message."
        ),
    )
    answered: bool = Field(
        ...,
        description=(
            'INTERNAL flag, never written in the reply text. Whether the '
            'assistant actually helped the user. '
            'Set True when you provided the requested information OR '
            "appropriately handled a greeting, a meta-question ('what can "
            "you do?'), or a recommendation using the available context. "
            'Set False when the requested information was not available '
            "(empty context or a topic outside the subject's scope) and you "
            'returned the fallback apology, OR when the message had no real '
            'question to answer (gibberish / unintelligible / empty) and '
            'your reply just asks the user to rephrase. A real, useful '
            'answer is always True. '
            'Do NOT pre-judge: if the RAG context contains information '
            'relevant to the question, you must answer from it and set True '
            '— partial context is still True. False requires that you '
            'genuinely had nothing relevant to use.'
        ),
    )
    category: str = Field(
        ...,
        description=(
            "Topic category of the question in English (e.g. 'personal life', "
            "'projects', 'skills', 'contact'). Use 'unknown' if unclear."
        ),
    )
