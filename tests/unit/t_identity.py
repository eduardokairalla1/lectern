"""
Unit tests for loading and validating the identity file.
"""

# --- IMPORTS ---
from pathlib import Path
from src.identity import IdentityConfig
from src.identity import Persona
from src.identity import get_identity

import pydantic
import pytest
import yaml


# --- HELPERS ---
MINIMAL = {
    'identity': {'name': 'TARS'},
    'persona': {'subject': 'TARS', 'scope': 'his mission', 'character': 'dry'},
}


def _write(tmp_path: Path, doc: dict) -> Path:
    """Writes an identity document and returns its path."""
    path = tmp_path / 'identity.yaml'
    path.write_text(yaml.safe_dump(doc), encoding='utf-8')
    return path


@pytest.fixture(autouse=True)
def _clear_cache():
    """The loader is cached per process, so each test starts clean."""
    get_identity.cache_clear()
    yield
    get_identity.cache_clear()


# --- CODE ---
class TestSubject:

    def test_requires_a_name(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            IdentityConfig(identity={}, persona=MINIMAL['persona'])

    def test_accepts_arbitrary_extra_fields(self) -> None:
        config = IdentityConfig(
            identity={'name': 'TARS', 'role': 'robot', 'humor': 75},
            persona=MINIMAL['persona'],
        )
        assert config.identity.model_dump()['humor'] == 75

    def test_accepts_nested_structures(self) -> None:
        # the profile is served verbatim, so it must not flatten anything
        config = IdentityConfig(
            identity={'name': 'TARS', 'settings': {'humor': 75}},
            persona=MINIMAL['persona'],
        )
        assert config.identity.model_dump()['settings'] == {'humor': 75}


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


class TestGetIdentity:

    def test_loads_the_configured_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            'src.identity.config.IDENTITY_FILE', str(_write(tmp_path, MINIMAL))
        )
        assert get_identity().identity.name == 'TARS'

    def test_missing_file_fails_loudly(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # answering as nobody is worse than not starting
        monkeypatch.setattr(
            'src.identity.config.IDENTITY_FILE', str(tmp_path / 'absent.yaml')
        )
        with pytest.raises(FileNotFoundError):
            get_identity()

    def test_is_read_once_per_process(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = _write(tmp_path, MINIMAL)
        monkeypatch.setattr('src.identity.config.IDENTITY_FILE', str(path))
        first = get_identity()

        path.write_text(
            yaml.safe_dump({**MINIMAL, 'identity': {'name': 'CASE'}}),
            encoding='utf-8',
        )
        assert get_identity() is first

    def test_the_shipped_example_is_valid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # it is the starting point for every self-hosted deployment
        monkeypatch.setattr(
            'src.identity.config.IDENTITY_FILE', 'identity.example.yaml'
        )
        identity = get_identity()
        assert identity.identity.name
        assert identity.persona.examples
