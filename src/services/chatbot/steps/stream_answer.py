"""
Stream tokens from the LLM.
"""

# --- IMPORTS ---
from collections.abc import AsyncGenerator
from src.clients.llms import ASSISTANT_LLM
from src.clients.llms import MEMORY_LLM
from src.config import config
from src.schemas.outputparser import ResponseOutputParser
from src.services.chatbot.events import classify_stream_error
from src.services.chatbot.events import error_event
from src.services.chatbot.events import sanitize_output
from src.services.chatbot.events import stream_end_event
from src.services.chatbot.events import strip_meta_artifacts
from src.services.chatbot.events import token_event
from src.services.chatbot.prompts import build_answer_prompt
from src.services.chatbot.prompts import build_metadata_prompt
from src.services.chatbot.types import AnswerMetadata
from src.services.chatbot.types import Execution
from src.services.chatbot.types import State
from src.services.chatbot.types import StreamEvent

import asyncio
import json
import logging
import openai


# --- GLOBALS ---
logger = logging.getLogger(__name__)

MAX_STREAMING_DURATION_SECONDS = 60

# classification used when the metadata step can't produce one
DEFAULT_METADATA: AnswerMetadata = {'answered': True, 'category': 'general'}


# --- CODE ---
async def stream_answer(state: State) -> AsyncGenerator[StreamEvent, None]:
    """
    Stream tokens from LLM.

    :param state: The current state of the chatbot session.

    :return: AsyncGenerator yielding StreamEvent objects.
    """
    # build the prompt for the LLM
    prompt = build_answer_prompt(
        message=state['message'],
        history=state['memoryText'],
        context=state['context'],
    )

    # initialize variables for the full response and token usage
    full_response = ''
    usage = {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}

    logger.debug(
        f'[Streaming] Starting token stream. '
        f'Exchange: {state["exchangeId"]}'
    )

    # stream tokens from the LLM with a timeout
    try:

        # start timout
        async with asyncio.timeout(MAX_STREAMING_DURATION_SECONDS):

            # stream tokens from the LLM
            async for chunk in ASSISTANT_LLM.astream(prompt, stream_usage=True):

                # chunk has text: sanitize it and yield a token event
                if chunk.text:
                    sanitized_content = sanitize_output(chunk.text)
                    full_response += chunk.text
                    yield token_event(sanitized_content)

                # chunk has usage metadata: update the usage dictionary
                um = getattr(chunk, 'usage_metadata', None) or {}
                usage = {
                    key: um.get(key) or current
                    for key, current in usage.items()
                }

    # timeout: token stream took too long
    except (TimeoutError, openai.APIError) as exc:
        code, msg = classify_stream_error(exc)
        logger.warning(
            f'[Streaming] Token stream failed ({code}). '
            f'Exchange: {state["exchangeId"]}, Error: {exc}'
        )
        yield error_event(code, msg)
        return

    # streaming complete: strip any meta artifacts from the full response
    full_response = strip_meta_artifacts(full_response)

    logger.debug(
        f'[Streaming] Token stream complete. '
        f'Exchange: {state["exchangeId"]}, Length: {len(full_response)}'
    )

    # yield the stream end event to signal the end of the token stream
    yield stream_end_event()

    # derive answered/category metadata from context or LLM
    metadata = derive_metadata_from_context(
        full_response,
        state
    ) or await extract_metadata(full_response, state)

    # update usage with total tokens if not provided
    usage['total_tokens'] = (
        usage['total_tokens'] or usage['input_tokens'] + usage['output_tokens']
    )

    # append the execution record to the state
    state['execution'].append(
        Execution(
            execution_type='chatbot_answer',
            llm_model=config.PRINCIPAL_MODEL,
            input_tokens=usage['input_tokens'],
            output_tokens=usage['output_tokens'],
            total_tokens=usage['total_tokens'],
        )
    )

    # update the state with the full response and metadata
    state['response'] = ResponseOutputParser(
        response=full_response,
        answered=metadata['answered'],
        category=metadata['category'],
    )


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
