"""
Audio message resolver.
"""

# --- IMPORTS ---
from src.services.chatbot.prompts import TRANSCRIPTION_PROMPT
from src.services.chatbot.types import ChatMessage
from src.utils.transcribe import transcribe_audio


# --- CODE ---
async def resolve_audio(chat_message: ChatMessage) -> str:
    """
    Resolves an audio message: transcribes the base64 payload to text.

    :param chat_message: The resolved chat message input.

    :raises AssertionError: If the audio_base64 field is not present in the
                            chat message.

    :return: The transcribed message text.
    """
    # ensure the audio_base64 field is present
    assert chat_message.audio_base64 is not None

    # transcribe the audio
    return await transcribe_audio(
        chat_message.audio_base64,
        prompt=TRANSCRIPTION_PROMPT
    )
