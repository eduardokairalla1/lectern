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


