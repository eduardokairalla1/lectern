"""
The subject this instance speaks for.
"""

# --- IMPORTS ---
from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from src.config import config

import yaml


# --- CODE ---
class Example(BaseModel):
    """
    One few-shot exchange, teaching voice and formatting to the model.
    """
    user: str = Field(
        description='The visitor message, optionally prefixed with the '
                    'scenario in parentheses.',
    )
    reply: str = Field(description='The complete answer the model should '
                                   'have produced.')


class Persona(BaseModel):
    """
    How the assistant talks about the subject.
    """
    model_config = ConfigDict(extra='forbid')

    subject: str = Field(
        description='Name used inside the prompt when referring to the '
                    'subject.',
    )
    short_name: str = Field(
        default='',
        description='Informal form used in casual references inside the '
                    'prompt. Defaults to the subject itself.',
    )
    scope: str = Field(
        description='What the assistant is allowed to talk about. Anything '
                    'else is declined.',
    )
    character: str = Field(
        description="The assistant's own voice and personality, injected "
                    'verbatim into the system prompt.',
    )
    corpus_language: str = Field(
        default='English',
        description='Language the source documents are written in. The '
                    "assistant still replies in the visitor's language.",
    )
    baseline_summary: str = Field(
        default='',
        description='Facts that are always available, used when retrieval '
                    'returns nothing specific.',
    )
    examples: list[Example] = Field(
        default_factory=list,
        description='Few-shot exchanges appended to the system prompt.',
    )


    def casual_name(self) -> str:
        """
        The informal name, falling back to the full subject.

        :return: Name to use in casual references.
        """
        return self.short_name or self.subject


class Subject(BaseModel):
    """
    The public profile served by GET /whoami.
    """
    model_config = ConfigDict(extra='allow')

    name: str


class IdentityConfig(BaseModel):
    """
    Full contents of the identity file.
    """
    model_config = ConfigDict(extra='forbid')

    identity: Subject
    persona: Persona


@lru_cache(maxsize=1)
def get_identity() -> IdentityConfig:
    """
    Loads and validates the identity file.

    Cached: the file is deployment configuration, read once per process.

    :raises FileNotFoundError: If the configured file does not exist.

    :return: The parsed identity configuration.
    """
    # get identity path
    path = Path(config.IDENTITY_FILE)

    # identity file does not exist: raise a FileNotFoundError
    if not path.is_file():
        raise FileNotFoundError(
            f'Identity file not found at {path}. Copy '
            f'identity.example.yaml and point IDENTITY_FILE at it.'
        )

    # load identity config and return
    return IdentityConfig(**yaml.safe_load(path.read_text(encoding='utf-8')))
