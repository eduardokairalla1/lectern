"""
Retrieve documents step.
"""

# --- IMPORTS ---
from langchain_core.documents import Document

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


