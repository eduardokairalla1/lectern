"""
Text message resolver.
"""

# --- IMPORTS ---
from src.services.chatbot.types import ChatMessage


# --- CODE ---
async def resolve_text(chat_message: ChatMessage) -> str:
    """
    Resolves a text message: the content IS the message.

    :param chat_message: The resolved chat message input.

    :return: The message text.
    """
    return chat_message.content
