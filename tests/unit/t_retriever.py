"""
Unit tests for the retriever step's filtering and formatting.
"""

# --- IMPORTS ---
from langchain_core.documents import Document
from src.services.chatbot.steps.retriever import _clean_text


# --- HELPERS ---
def _doc(text: str = 'clean', page: str = 'page', **metadata: str) -> Document:
    """Builds a document carrying both the clean text and page_content."""
    return Document(page_content=page, metadata={'text': text, **metadata})


# --- CODE ---
class TestCleanText:

    def test_prefers_the_clean_metadata_text(self) -> None:
        assert _clean_text(_doc(text='clean', page='breadcrumb')) == 'clean'

    def test_falls_back_to_page_content_when_absent(self) -> None:
        doc = Document(page_content='only page', metadata={})
        assert _clean_text(doc) == 'only page'

    def test_falls_back_when_the_metadata_text_is_empty(self) -> None:
        doc = Document(page_content='only page', metadata={'text': ''})
        assert _clean_text(doc) == 'only page'


