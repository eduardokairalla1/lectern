"""
The chatbot pipeline's own vocabulary.
"""

# --- IMPORTS ---
from dataclasses import dataclass
from langchain_core.messages import BaseMessage
from src.schemas.endpoints.chatbot_response import ChatbotPayload
from src.types.executions import ExecutionType
from typing import TypedDict


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


# --- PIPELINE ---
@dataclass
class Execution:
    """
    A single LLM call made during the pipeline.
    """
    execution_type: ExecutionType
    llm_model: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None

    @classmethod
    def from_message(
        cls,
        message: BaseMessage,
        execution_type: ExecutionType,
        default_model: str = 'unknown',
    ) -> 'Execution':
        """
        Builds an Execution from a LangChain message, reading the model
        name and token usage the provider reported.

        :param message: LLM response message (usually an AIMessage).
        :param execution_type: Tag identifying this execution's role.
        :param default_model: Model name to use if the provider didn't
            report one in response_metadata.

        :return: The resulting Execution.
        """
        usage = getattr(message, 'usage_metadata', None) or {}
        response_metadata = getattr(message, 'response_metadata', None) or {}
        return cls(
            execution_type=execution_type,
            llm_model=response_metadata.get('model_name', default_model),
            input_tokens=usage.get('input_tokens'),
            output_tokens=usage.get('output_tokens'),
            total_tokens=usage.get('total_tokens'),
        )


# --- CACHE ---
class CachedResponse(TypedDict):
    """
    Cached assistant response, keyed by normalized query.
    """
    response: str
    answered: bool
    category: str
