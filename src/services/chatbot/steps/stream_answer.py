"""
Stream tokens from the LLM.
"""

# --- IMPORTS ---
from src.clients.llms import MEMORY_LLM
from src.config import config
from src.services.chatbot.prompts import build_metadata_prompt
from src.services.chatbot.types import AnswerMetadata
from src.services.chatbot.types import Execution
from src.services.chatbot.types import State

import json
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


async def extract_metadata(response: str, state: State) -> AnswerMetadata:
    """
    Extract answered/category metadata with fast LLM after streaming.

    :param response: The full response text.
    :param state: The current state of the chatbot session.

    :return: Dictionary with answered and category fields.
    """
    # build the prompt for metadata extraction
    prompt_text = build_metadata_prompt(response)

    # run the metadata extraction LLM
    try:
        result = await MEMORY_LLM.ainvoke(prompt_text)

    # model call failed (timeout, rate limit, outage): use defaults
    except Exception as e:
        logger.warning(
            f'[Streaming] Metadata extraction call failed: {e}. '
            f'Using defaults.'
        )
        return DEFAULT_METADATA.copy()

    # append the metadata extraction execution to the state
    state['execution'].append(
        Execution.from_message(
            result, 'metadata_extraction', config.MEMORY_MODEL
        )
    )

    # parse the metadata from the LLM response
    content = result.text.strip()

    # content is wrapped in ```json ... ```: extract the JSON part
    if content.startswith('```'):
        content = content.split('```')[1].removeprefix('json').strip()

    # parse the JSON content and return it. The model is asked for JSON but
    # is not guaranteed to produce it, so a decode failure is expected.
    try:
        return json.loads(content)

    # response was not valid JSON: use defaults
    except json.JSONDecodeError as e:
        logger.warning(
            f'[Streaming] Metadata is not valid JSON: {e}. '
            f'Using defaults ({len(content)} chars returned).'
        )
        return DEFAULT_METADATA.copy()
