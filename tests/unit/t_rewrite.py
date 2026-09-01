"""
Unit tests for the query rewrite step.
"""

# --- IMPORTS ---
from langchain_core.messages import AIMessage
from src.schemas.outputparser import RewriteOutputParser
from src.services.chatbot.steps.rewrite import rewrite_query
from src.services.chatbot.types import State
from typing import Any

import pytest


# --- HELPERS ---
def _state(**overrides: Any) -> State:
    """Builds a state carrying context, so the step reaches the model."""
    state: State = {
        'sessionId': 's-1',
        'exchangeId': 'e-1',
        'context': '',
        'rewrittenQuery': '',
        'language': '',
        'recentInteractions': [('Where does he work?', 'At Vulcanet.')],
        'memoryText': '',
        'message': 'and before that?',
        'response': None,
        'execution': [],
    }
    state.update(overrides)  # type: ignore[typeddict-item]
    return state


class FakeModel:
    """
    Stand-in for STRUCTURED_REWRITE_MODEL.

    `result` is returned from ainvoke; `error` is raised instead when set.
    """

    def __init__(self, result: Any = None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls = 0

    async def ainvoke(self, _prompt: Any) -> Any:
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def _reply(query: str, language: str) -> dict[str, Any]:
    """Builds what with_structured_output(include_raw=True) returns."""
    return {
        'raw': AIMessage(
            content='',
            response_metadata={'model_name': 'gpt-test'},
            usage_metadata={
                'input_tokens': 10,
                'output_tokens': 4,
                'total_tokens': 14,
            },
        ),
        'parsed': RewriteOutputParser(query=query, language=language),
        'parsing_error': None,
    }


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch):
    """Installs a fake rewrite model and hands it back for assertions."""

    def install(**kwargs: Any) -> FakeModel:
        fake = FakeModel(**kwargs)
        monkeypatch.setattr(
            'src.services.chatbot.steps.rewrite.STRUCTURED_REWRITE_MODEL',
            fake,
        )
        return fake

    return install


# --- CODE ---
class TestWithoutContext:

    @pytest.mark.anyio
    async def test_keeps_the_original_query_and_never_calls_the_model(
        self, model
    ) -> None:
        # the first message of a session has nothing to resolve against, so
        # paying for a rewrite would buy nothing
        fake = model()
        state = await rewrite_query(_state(recentInteractions=[]))
        assert state['rewrittenQuery'] == 'and before that?'
        assert fake.calls == 0
        assert state['execution'] == []

    @pytest.mark.anyio
    async def test_leaves_the_language_unset(self, model) -> None:
        # nothing detected it, and build_answer_prompt reads '' as "infer it"
        model()
        state = await rewrite_query(_state(recentInteractions=[]))
        assert state['language'] == ''


class TestSuccessfulRewrite:

    @pytest.mark.anyio
    async def test_stores_the_rewritten_query(self, model) -> None:
        model(result=_reply('Where did he work before Vulcanet?', 'English'))
        state = await rewrite_query(_state())
        assert state['rewrittenQuery'] == 'Where did he work before Vulcanet?'

    @pytest.mark.anyio
    async def test_stores_the_detected_language(self, model) -> None:
        # this is the whole reason the call returns structured output: a
        # two-word follow-up is only classifiable against the history
        model(result=_reply('rewritten', 'Portuguese'))
        state = await rewrite_query(_state(message='sim'))
        assert state['language'] == 'Portuguese'

    @pytest.mark.anyio
    async def test_records_the_execution_from_the_raw_message(
        self, model
    ) -> None:
        # token usage lives on the raw message, not the parsed model
        model(result=_reply('rewritten', 'English'))
        state = await rewrite_query(_state())
        execution = state['execution'][0]
        assert execution.execution_type == 'query_rewrite'
        assert execution.llm_model == 'gpt-test'
        assert execution.total_tokens == 14

    @pytest.mark.anyio
    async def test_strips_surrounding_whitespace(self, model) -> None:
        model(result=_reply('  rewritten  ', '  English  '))
        state = await rewrite_query(_state())
        assert state['rewrittenQuery'] == 'rewritten'
        assert state['language'] == 'English'

    @pytest.mark.anyio
    async def test_an_empty_query_falls_back_to_the_message(
        self, model
    ) -> None:
        # an empty search query would retrieve nothing at all
        model(result=_reply('   ', 'English'))
        state = await rewrite_query(_state())
        assert state['rewrittenQuery'] == 'and before that?'


class TestDegradation:
    """
    Losing the rewrite costs some retrieval quality; raising would cost the
    answer entirely. Both failure modes degrade instead of propagating.
    """

    @pytest.mark.anyio
    async def test_a_failed_call_keeps_the_original_query(self, model) -> None:
        model(error=RuntimeError('provider is down'))
        state = await rewrite_query(_state())
        assert state['rewrittenQuery'] == 'and before that?'
        assert state['execution'] == []
        assert state['language'] == ''

    @pytest.mark.anyio
    async def test_unparsed_structured_output_keeps_the_original_query(
        self, model
    ) -> None:
        # the call itself succeeds, so the except clause never sees this: the
        # model returned something that did not fit the schema
        model(result={
            'raw': AIMessage(content='not json'),
            'parsed': None,
            'parsing_error': ValueError('malformed'),
        })
        state = await rewrite_query(_state())
        assert state['rewrittenQuery'] == 'and before that?'
        assert state['execution'] == []
        assert state['language'] == ''
