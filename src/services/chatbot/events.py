"""
Server-Sent Events (SSE) for the chatbot.
"""

# --- IMPORTS ---

import html
import re


# --- META-ARTIFACT STRIPPING ---
# Safety net: the assistant must never write internal fields in its reply
# (enforced in the system prompt), but if a leak like a trailing
# "answered = true" / "category: ..." / "Justification: ..." ever slips through
# the streamed text, we strip it before the response is stored or cached so it
# can't be persisted and re-served to other users.
_META_TAIL = re.compile(
    r'\s*(?:'
    r'answered\s*[:=]\s*(?:true|false)'
    r'|category\s*[:=].*'
    r'|reasoning\s*[:=].*'
    r'|justification\s*:.*'
    r')\s*$',
    re.IGNORECASE,
)


def strip_meta_artifacts(text: str) -> str:
    """
    Remove trailing internal-metadata lines the model may have accidentally
    appended to its reply (answered/category/reasoning/justification).

    :param text: Raw response text.
    :return: Text with trailing metadata artifacts removed.
    """
    if not text:
        return text

    previous = None
    while previous != text:
        previous = text
        text = _META_TAIL.sub('', text)

    return text.rstrip()


# --- OUTPUT SANITIZATION ---
def sanitize_output(text: str) -> str:
    """
    Sanitize LLM output to prevent XSS attacks.
    Escapes HTML special characters while preserving markdown.

    :param text: Raw text from LLM.
    :return: Sanitized text safe for SSE transmission.
    """
    if not text:
        return text

    # Escape HTML entities to prevent XSS.
    # This preserves markdown syntax but escapes <script>, <img onerror>, etc.
    sanitized = html.escape(text, quote=False)

    return sanitized


