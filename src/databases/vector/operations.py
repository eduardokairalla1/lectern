"""
Vector database operations.
"""

# --- IMPORTS ---
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client.http.exceptions import ResponseHandlingException
from src.clients.llms import EMBEDDING
from src.config import config
from src.errors.vector_store_unavailable_error import (
    VectorStoreUnavailableError,
)
from src.resources import get_resources

import httpx
import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)

_UNAVAILABLE_ERRORS = (
    ConnectionError,
    httpx.TransportError,
    ResponseHandlingException,
)

# vector store (lazy singleton)
_vector_store: QdrantVectorStore | None = None


# --- CODE ---
def _get_vector_store() -> QdrantVectorStore:
    """
    Returns the shared vector store, building it once on first use.

    :return: The shared vector store instance.
    """
    # reference the global variable
    global _vector_store

    # vector store is not yet created: create it
    if _vector_store is None:
        _vector_store = QdrantVectorStore(
            client=get_resources().vector_client,
            collection_name=config.VECTOR_COLLECTION,
            embedding=EMBEDDING,
        )

    # return the vector store
    return _vector_store


async def search(query: str, limit: int) -> list[tuple[Document, float]]:
    """
    Runs a similarity search, returning each match with its score.

    :param query: The text to search for.
    :param limit: Maximum number of matches to return.

    :raises VectorStoreUnavailableError: If the vector database is
        unreachable.

    :return: List of (document, similarity score) tuples.
    """
    # search the vector store
    try:
        results = await _get_vector_store().asimilarity_search_with_score(
            query=query,
            k=limit
        )
        logger.debug('Vector search returned %s matches', len(results))

        # return the matches with their scores
        return results

    # vector database is unreachable: raise VectorStoreUnavailableError
    except _UNAVAILABLE_ERRORS as e:
        raise VectorStoreUnavailableError(
            {'operation': 'search', 'error': str(e)}
        ) from e
