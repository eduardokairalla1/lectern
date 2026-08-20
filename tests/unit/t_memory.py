"""
Unit tests for the conversation memory (summary + recent interactions).
"""

# --- IMPORTS ---
from src.services.chatbot import memory


# --- CODE ---
class TestKeys:

    def test_summary_and_recent_keys_are_distinct(self) -> None:
        # both live in Redis under the same session; colliding would make a
        # summary overwrite the raw interactions
        assert memory._summary_key('s-1') != memory._recent_key('s-1')

    def test_keys_are_namespaced_by_session(self) -> None:
        assert 's-1' in memory._summary_key('s-1')
        assert 's-1' in memory._recent_key('s-1')


class TestFormat:

    def test_returns_the_summary_alone_without_interactions(self) -> None:
        assert memory._format('summary', []) == 'summary'

    def test_appends_numbered_interactions(self) -> None:
        formatted = memory._format('summary', [('q1', 'a1'), ('q2', 'a2')])
        assert 'Question 1: q1' in formatted
        assert 'AI Response 2: a2' in formatted

    def test_keeps_the_summary_first(self) -> None:
        formatted = memory._format('summary', [('q', 'a')])
        assert formatted.startswith('summary')


