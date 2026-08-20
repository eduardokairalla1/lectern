"""
Unit tests for the conversation memory (summary + recent interactions).
"""

# --- IMPORTS ---
from src.resources import Resources
from src.services.chatbot import memory
from tests.unit.conftest import FakeRedis

import json
import pytest


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


class TestGetRecentInteractions:

    @pytest.mark.anyio
    async def test_returns_empty_when_nothing_is_stored(
        self, resources: Resources
    ) -> None:
        assert await memory.get_recent_interactions('s-1') == []

    @pytest.mark.anyio
    async def test_parses_stored_pairs(
        self, resources: Resources, fake_redis: FakeRedis
    ) -> None:
        fake_redis.data[memory._recent_key('s-1')] = json.dumps(
            [{'input': 'q', 'response': 'a'}]
        )
        assert await memory.get_recent_interactions('s-1') == [('q', 'a')]


class TestUpdateRecentInteractions:

    @pytest.mark.anyio
    async def test_stores_the_first_interaction(
        self, resources: Resources
    ) -> None:
        await memory.update_recent_interactions('s-1', 'q', 'a')
        assert await memory.get_recent_interactions('s-1') == [('q', 'a')]

    @pytest.mark.anyio
    async def test_appends_in_chronological_order(
        self, resources: Resources
    ) -> None:
        await memory.update_recent_interactions('s-1', 'q1', 'a1')
        await memory.update_recent_interactions('s-1', 'q2', 'a2')
        assert await memory.get_recent_interactions('s-1') == [
            ('q1', 'a1'), ('q2', 'a2')
        ]

    @pytest.mark.anyio
    async def test_keeps_only_the_most_recent_ones(
        self, resources: Resources
    ) -> None:
        for i in range(memory.MAX_RECENT_INTERACTIONS + 2):
            await memory.update_recent_interactions('s-1', f'q{i}', f'a{i}')

        stored = await memory.get_recent_interactions('s-1')
        assert len(stored) == memory.MAX_RECENT_INTERACTIONS
        assert stored[-1] == (
            f'q{memory.MAX_RECENT_INTERACTIONS + 1}',
            f'a{memory.MAX_RECENT_INTERACTIONS + 1}',
        )

    @pytest.mark.anyio
    async def test_sessions_do_not_share_interactions(
        self, resources: Resources
    ) -> None:
        await memory.update_recent_interactions('s-1', 'q', 'a')
        assert await memory.get_recent_interactions('s-2') == []


