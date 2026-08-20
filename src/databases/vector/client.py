"""
Vector database client factory.
"""

# --- IMPORTS ---
from qdrant_client import QdrantClient


# --- CODE ---
def vector_client_factory(url: str) -> QdrantClient:
    """
    Creates the vector database client.

    :param url: The URL of the vector database service.

    :return: An instance of the vector database client.
    """
    return QdrantClient(url=url)
