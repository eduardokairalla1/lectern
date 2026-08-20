"""
Central prompt registry.
"""

# --- IMPORTS ---
from langchain_core.messages import BaseMessage
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
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
# NOTE: the reformulated query is intentionally produced in the language of
#       the indexed knowledge base, because matching the query language to the
#       documents maximizes retrieval recall.
REWRITE_SYSTEM_TEMPLATE = """
You are a specialist in query reformulation for semantic search.

<objective>
Transform the user question into an optimized query for vector search,
resolving ambiguous references using the conversation context.
</objective>

<rules>
- If the question is clear and self-contained: return it as is
- If there are pronouns/vague references ("this", "it", "that", "more"):
  replace with the concrete term from context
- Maintain the original intent of the question
- Return ONLY the reformulated query, no explanations
- ALWAYS write the reformulated query in [[corpus_language]], regardless of
  the question language
</rules>
"""


REWRITE_SYSTEM_PROMPT = _render(REWRITE_SYSTEM_TEMPLATE)


# initial summary for a new conversation (no prior context)
INITIAL_SUMMARY = 'This is the beginning of the conversation. No prior context.'


# resume memory prompt
RESUME_SYSTEM_PROMPT = """
You are a specialist in incremental conversation summarization.

<guidelines>
When updating summaries, ALWAYS:
• Integrate new relevant information into the existing context
• Preserve: user identity, main objective, critical preferences,
  conversation progression
• Remove: redundancies, outdated information, irrelevant details
• Maintain chronology: the most recent information takes priority over
  older information
</guidelines>

<output_format>
Return ONLY the updated summary, without:
- Prefixes such as "Updated summary:" or "New summary:"
- Explanations about the changes made
- Comments or metadata
</output_format>
"""


# condense memory prompt
CONDENSE_SYSTEM_PROMPT = """
You are a specialist in information synthesis. Your role is to extract and
condense only critical data from extensive summaries.

<guidelines>
ALWAYS include only:
• User identity (name, role, context)
• Main objective of the conversation
• Critical preferences or requirements
• Most recent relevant action or state

ALWAYS exclude:
• Redundant or secondary details
• Information already implied in the context
• Generic descriptions or obvious statements
</guidelines>

<output_format>
Return ONLY the condensed text in 3-4 lines, without:
- Titles or headers
- Prefixes such as "Summary:" or "Condensed:"
- Explanations about the process
- Bullets or markers
</output_format>
"""


# transcription prompt for audio messages
TRANSCRIPTION_TEMPLATE = """
Voice message for an assistant that answers about [[subject]]. The user may
ask about [[scope]].
"""


TRANSCRIPTION_PROMPT = _render(TRANSCRIPTION_TEMPLATE)


# --- CODE ---
def build_rewrite_prompt(query: str, context: str) -> list[BaseMessage]:
    """
    Builds the query-rewrite prompt.

    :param query: The user's original question.
    :param context: Formatted recent conversation context.

    :return: List of formatted prompt messages.
    """
    # build the human message content
    human_content = (
        f'<conversation_context>\n{context}\n</conversation_context>\n\n'
        f'<user_question>\n{query}\n</user_question>\n\n'
        'Reformulated query:'
    )

    # return the prompt messages
    return [
        SystemMessage(content=REWRITE_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]


def build_resume_prompt(
    summary: str,
    user_input: str,
    response: str
) -> list[BaseMessage]:
    """
    Builds the incremental memory-summary prompt.

    :param summary: Current conversation summary.
    :param user_input: Latest user message.
    :param response: Assistant reply.

    :return: List of formatted prompt messages.
    """
    # build the human message content
    human_content = (
        f'<current_summary>\n{summary}\n</current_summary>\n\n'
        '<new_interaction>\n'
        f'User: {user_input}\n'
        f'Assistant: {response}\n'
        '</new_interaction>\n\n'
        'Generate the updated summary integrating the new information.'
    )

    # return the prompt messages
    return [
        SystemMessage(content=RESUME_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]


def build_condense_prompt(summary: str) -> list[BaseMessage]:
    """
    Builds the summary-condensation prompt.

    :param summary: Oversized conversation summary to condense.

    :return: List of formatted prompt messages.
    """
    # build the human message content
    human_content = (
        f'<original_summary>\n{summary}\n</original_summary>\n\n'
        'Condense the summary above following your guidelines.'
    )

    # return the prompt messages
    return [
        SystemMessage(content=CONDENSE_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]
