"""
Retrieve documents step.
"""

# --- IMPORTS ---
from langchain_core.documents import Document
from src.databases.vector import operations
from src.errors.processing_error import ProcessingError
from src.services.chatbot.types import State
from src.types.documents import RetrievedDocument

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 0.3
MAX_DOCUMENTS = 4


# --- CODE ---
def _clean_text(doc: Document) -> str:
    """
    Returns the document's clean text.

    :param doc: The retrieved document.

    :return: The document's clean text.
    """
    return doc.metadata.get('text') or doc.page_content


def _to_retrieved_document(
    doc: Document,
    score: float,
    index: int
) -> RetrievedDocument:
    """
    Build the raw document record persisted with the exchange.

    :param doc: The accepted document.
    :param score: Its similarity score.
    :param index: Its 1-based position among the accepted documents.

    :return: The raw document record for database storage.
    """
    return {
        'title': doc.metadata.get('section')
        or doc.metadata.get('category')
        or f'Document {index}',
        'score': float(score),
        'content': _clean_text(doc)[:500],
        'metadata': {
            'category': doc.metadata.get('category'),
            'section': doc.metadata.get('section'),
            'type': doc.metadata.get('type'),
        },
    }


def _filter_documents(
    docsWithScores: list[tuple[Document, float]],
    session_id: str
) -> list[tuple[Document, float]]:
    """
    Filter retrieved documents by score threshold and deduplicate by content.

    :param docsWithScores: List of (document, score) tuples from the
        vector store.
    :param session_id: Session identifier, used for logging.

    :return: The accepted (document, score) tuples, in relevance order.
    """
    # filter by score threshold and deduplicate by content hash
    accepted: list[tuple[Document, float]] = []
    seenContent = set()

    # iterate over the documents
    for doc, score in docsWithScores:

        # score is below the threshold: skip it and log the reason
        if score < SCORE_THRESHOLD:
            logger.debug(
                f'[Step: retriever] Skipping low-score doc '
                f'(score={score:.3f}). Session: {session_id}'
            )
            continue

        # content hash is a duplicate: skip it and log the reason
        contentHash = _clean_text(doc)[:100]
        if contentHash in seenContent:
            logger.debug(
                f'[Step: retriever] Skipping duplicate doc. '
                f'Session: {session_id}'
            )
            continue

        # content is unique and score is above the threshold: accept it
        seenContent.add(contentHash)
        accepted.append((doc, score))

        # log the accepted document's score and category
        category = doc.metadata.get('category', 'unknown')
        logger.debug(
            f'[Step: retriever] Doc accepted: score={score:.3f}, '
            f'category={category}. Session: {session_id}'
        )

        # maximum number of documents: stop accepting more
        if len(accepted) >= MAX_DOCUMENTS:
            break

    # return the accepted documents
    return accepted


def format_documents(docs: list[Document]) -> str:
    """
    Format retrieved documents into structured text for the LLM.

    :param docs: List of retrieved documents.

    :return: Formatted string with document contents.
    """
    # no documents: return a placeholder message
    if not docs:
        return 'No relevant documents found.'

    # build the formatted string with document headers and content
    formatted = []
    for i, doc in enumerate(docs, 1):
        content = _clean_text(doc).strip()
        labels = {
            'Category': doc.metadata.get('category'),
            'Section': doc.metadata.get('section'),
        }
        header_parts = [f'[Document {i}]'] + [
            f'{label}: {value}' for label, value in labels.items() if value
        ]
        header = ' | '.join(header_parts)
        formatted.append(f'{header}\n{content}')

    # return the formatted documents
    return '\n\n'.join(formatted)


async def retriever(state: State) -> State:
    """
    Retrieve relevant documents from the vector store and update the state.

    :param state: The current state of the chatbot session.

    :return: The updated state, with the 'context' field containing the
        formatted documents.
    """
    # get the query
    query = state.get('rewrittenQuery') or state['message']

    logger.debug(
        f'[Step: retriever] Searching ({len(query)} chars). '
        f'Exchange: {state["exchangeId"]}'
    )

    # retrieve documents from the vector store
    docsWithScores = await operations.search(
        query=query,
        limit=MAX_DOCUMENTS + 2
    )

    # process the retrieved documents
    try:

        # filter by score threshold and deduplicate
        accepted = _filter_documents(docsWithScores, state['sessionId'])
        filteredDocs = [doc for doc, _ in accepted]

        # update the 'context' field with formatted text
        state['context'] = format_documents(filteredDocs)

        # save raw docs with scores
        state['retrievedDocuments'] = [
            _to_retrieved_document(doc, score, i)
            for i, (doc, score) in enumerate(accepted, 1)
        ]

    # unexpected error while processing the documents: raise a 500 error
    except Exception as e:
        logger.error(
            f'[Step: retriever] Document processing error. '
            f'Exchange: {state["exchangeId"]}, Error: {str(e)}',
            exc_info=True,
        )
        raise ProcessingError({'error': str(e)}) from e

    logger.info(
        f'[Step: retriever] Retrieved {len(filteredDocs)} documents '
        f'(filtered from {len(docsWithScores)}). '
        f'Session: {state["sessionId"]}'
    )

    # return the updated state with the new context
    return state
