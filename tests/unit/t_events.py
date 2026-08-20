"""
Unit tests for the SSE event constructors and error classification.
"""

# --- IMPORTS ---
from src.services.chatbot.events import sanitize_output


# --- OUTPUT SANITIZATION ---
class TestSanitizeOutput:

    def test_escapes_html_special_characters(self) -> None:
        assert sanitize_output('<script>') == '&lt;script&gt;'

    def test_escapes_ampersand_but_not_quotes(self) -> None:
        # quote=False: the text lands in element content, never in an
        # attribute, and escaping quotes would disfigure ordinary prose
        assert sanitize_output('a & "b"') == 'a &amp; "b"'

    def test_preserves_markdown_emphasis(self) -> None:
        assert sanitize_output('**bold** _it_') == '**bold** _it_'

    def test_empty_string_stays_empty(self) -> None:
        assert sanitize_output('') == ''

    def test_is_idempotent_only_on_plain_text(self) -> None:
        # escaping twice would double-encode, which is why the streaming path
        # sanitizes each token exactly once
        once = sanitize_output('<b>')
        assert sanitize_output(once) != once


