"""
Unit tests for the retriever step's filtering and formatting.
"""

# --- IMPORTS ---
from langchain_core.documents import Document
from src.services.chatbot.steps.retriever import MAX_DOCUMENTS
from src.services.chatbot.steps.retriever import SCORE_THRESHOLD
from src.services.chatbot.steps.retriever import _clean_text
from src.services.chatbot.steps.retriever import _filter_documents


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


class TestFilterDocuments:

    def test_keeps_documents_above_the_threshold(self) -> None:
        pairs = [(_doc(text='a'), 0.9), (_doc(text='b'), 0.5)]
        assert len(_filter_documents(pairs, 's-1')) == 2

    def test_drops_documents_below_the_threshold(self) -> None:
        pairs = [(_doc(text='a'), SCORE_THRESHOLD - 0.01)]
        assert _filter_documents(pairs, 's-1') == []

    def test_the_threshold_itself_is_kept(self) -> None:
        pairs = [(_doc(text='a'), SCORE_THRESHOLD)]
        assert len(_filter_documents(pairs, 's-1')) == 1

    def test_deduplicates_by_clean_text(self) -> None:
        # sibling chunks share a breadcrumb in page_content, so dedup must
        # look at the clean text or it would drop distinct documents
        pairs = [
            (_doc(text='same', page='crumb A'), 0.9),
            (_doc(text='same', page='crumb B'), 0.8),
        ]
        assert len(_filter_documents(pairs, 's-1')) == 1

    def test_different_clean_text_is_not_deduplicated(self) -> None:
        pairs = [
            (_doc(text='one', page='crumb'), 0.9),
            (_doc(text='two', page='crumb'), 0.8),
        ]
        assert len(_filter_documents(pairs, 's-1')) == 2

    def test_stops_at_the_document_cap(self) -> None:
        pairs = [(_doc(text=str(i)), 0.9) for i in range(MAX_DOCUMENTS + 3)]
        assert len(_filter_documents(pairs, 's-1')) == MAX_DOCUMENTS

    def test_empty_input_yields_nothing(self) -> None:
        assert _filter_documents([], 's-1') == []

    def test_preserves_relevance_order(self) -> None:
        pairs = [(_doc(text='first'), 0.9), (_doc(text='second'), 0.4)]
        accepted = _filter_documents(pairs, 's-1')
        assert [_clean_text(d) for d, _ in accepted] == ['first', 'second']


