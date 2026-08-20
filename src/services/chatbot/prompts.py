"""
Central prompt registry.
"""

# --- IMPORTS ---
from src.identity import get_identity


# --- HELPERS ---
def _render(template: str) -> str:
    """
    Fills the [[placeholders]] of a prompt template from the identity file.

    :param template: The raw template text.

    :return: The template with every placeholder replaced.
    """
    persona = get_identity().persona

    # build few-shot examples
    examples = '\n\n'.join(
        f'User {example.user}\nReply: "{example.reply}"'
        for example in persona.examples
    )

    # interate over persona to resolve placeholders
    for placeholder, value in (('subject', persona.subject),
                               ('short_name', persona.casual_name()),
                               ('scope', persona.scope),
                               ('character', persona.character),
                               ('corpus_language', persona.corpus_language),
                               ('examples', examples)):
        template = template.replace(f'[[{placeholder}]]', value)

    return template


# --- GLOBALS ---
# initial summary for a new conversation (no prior context)
INITIAL_SUMMARY = 'This is the beginning of the conversation. No prior context.'


# transcription prompt for audio messages
TRANSCRIPTION_TEMPLATE = """
Voice message for an assistant that answers about [[subject]]. The user may
ask about [[scope]].
"""


TRANSCRIPTION_PROMPT = _render(TRANSCRIPTION_TEMPLATE)

