"""
User message resolution shared by the streaming and non-streaming paths.
"""

# --- IMPORTS ---
from collections.abc import Awaitable
from collections.abc import Callable
from src.errors.unsupported_message_type_error import (
    UnsupportedMessageTypeError,
)
from src.services.chatbot.resolvers.audio import resolve_audio
from src.services.chatbot.resolvers.text import resolve_text
from src.services.chatbot.types import ChatMessage


# --- CONSTANTS ---
_MESSAGE_RESOLVERS: dict[str, Callable[[ChatMessage], Awaitable[str]]] = {
    'text': resolve_text,
    'audio': resolve_audio,
}


# --- CODE ---
async def resolve_message(chat_message: ChatMessage) -> str:
    """
    Resolve the user message from the chat message input.

    :param chat_message: The resolved chat message input.

    :raises UnsupportedMessageTypeError: If no resolver is registered for
        the message's type.

    :return: The resolved text message.
    """
    # get the resolver for the message type
    resolver = _MESSAGE_RESOLVERS.get(chat_message.message_type)

    # resolver is registered for the message type: raise an error
    if resolver is None:
        raise UnsupportedMessageTypeError()

    # run the resolver and return the resolved message
    return await resolver(chat_message)
