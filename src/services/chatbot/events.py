"""
Server-Sent Events (SSE) for the chatbot.
"""

# --- IMPORTS ---

import html


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


