"""
The chatbot pipeline's own vocabulary.
"""

# --- IMPORTS ---
from dataclasses import dataclass
from src.schemas.endpoints.chatbot_response import ChatbotPayload


# --- INPUT ---
@dataclass
class ChatMessage:
    """
    Resolved chat message input for the service layer.
    """
    session_id: str
    content: str
    message_type: str
    audio_base64: str | None

    @classmethod
    def from_payload(cls, payload: ChatbotPayload) -> 'ChatMessage':
        """
        Builds a ChatMessage from the validated HTTP request payload.

        :param payload: The validated chatbot request payload.

        :return: The resulting ChatMessage.
        """
        return cls(
            session_id=payload.sessionId,
            content=payload.message.content,
            message_type=payload.message.messageType,
            audio_base64=payload.message.audioBase64,
        )


