"""
Unit tests for loading and validating the identity file.
"""

# --- IMPORTS ---
from src.identity import Persona

import pydantic
import pytest


# --- HELPERS ---
MINIMAL = {
    'identity': {'name': 'TARS'},
    'persona': {'subject': 'TARS', 'scope': 'his mission', 'character': 'dry'},
}


# --- CODE ---
class TestPersona:

    def test_rejects_unknown_keys(self) -> None:
        # a typo here would silently fall back to a default, and a wrong
        # corpus language degrades retrieval instead of failing
        with pytest.raises(pydantic.ValidationError):
            # the invalid keyword is the point of the test
            Persona(
                subject='TARS',
                scope='s',
                character='c',
                corpus_lang='English',  # type: ignore[call-arg]
            )

    def test_requires_subject_scope_and_character(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            # the missing fields are the point of the test
            Persona(subject='TARS')  # type: ignore[call-arg]

    def test_casual_name_falls_back_to_the_subject(self) -> None:
        persona = Persona(subject='Ada Lovelace', scope='s', character='c')
        assert persona.casual_name() == 'Ada Lovelace'

    def test_casual_name_prefers_the_short_name(self) -> None:
        persona = Persona(
            subject='Ada Lovelace', short_name='Ada', scope='s', character='c'
        )
        assert persona.casual_name() == 'Ada'

    def test_examples_default_to_empty(self) -> None:
        assert Persona(subject='S', scope='s', character='c').examples == []


