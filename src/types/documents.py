"""
Retrieved document types.
"""

# --- IMPORTS ---
from typing import TypedDict


# --- CODE ---
class RetrievedDocumentMetadata(TypedDict):
    """
    Topic metadata carried by a retrieved document.
    """
    category: str | None
    section: str | None
    type: str | None


class RetrievedDocument(TypedDict):
    """
    A document retrieved from the vector store.
    """
    title: str
    score: float
    content: str
    metadata: RetrievedDocumentMetadata
