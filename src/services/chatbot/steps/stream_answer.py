"""
Stream tokens from the LLM.
"""

# --- IMPORTS ---
from src.services.chatbot.types import AnswerMetadata
from src.services.chatbot.types import State

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)

MAX_STREAMING_DURATION_SECONDS = 60

# classification used when the metadata step can't produce one
DEFAULT_METADATA: AnswerMetadata = {'answered': True, 'category': 'general'}


# --- CODE ---
def derive_metadata_from_context(
    response: str,
    state: State
) -> AnswerMetadata | None:
    """
    Derive answered/category metadata from the context of the response.

    :param response: The full assistant response text.
    :param state: The current state of the chatbot session.

    :return: Metadata dict, or None when it can't be derived from context.
    """
    # get the retrieved documents
    docs = state.get('retrievedDocuments') or []

    # no documents or empty response: return None
    if not docs or not response.strip():
        return None

    # get the top document's metadata and derive the category
    top_metadata = docs[0].get('metadata') or {}
    category = top_metadata.get('category') or 'general'

    # return the derived metadata
    return {'answered': True, 'category': category}


