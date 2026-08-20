"""
The subject this instance speaks for.
"""

# --- IMPORTS ---
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


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
