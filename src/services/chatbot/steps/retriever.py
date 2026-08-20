"""
Retrieve documents step.
"""

# --- IMPORTS ---
from langchain_core.documents import Document

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)

# --- CODE ---
def _clean_text(doc: Document) -> str:
    """
    Returns the document's clean text.

    :param doc: The retrieved document.

    :return: The document's clean text.
    """
    return doc.metadata.get('text') or doc.page_content


