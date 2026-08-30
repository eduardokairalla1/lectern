"""
The chatbot pipeline's own vocabulary.
"""

# --- IMPORTS ---
from dataclasses import dataclass
from langchain_core.messages import BaseMessage
from src.schemas.endpoints.chatbot_response import ChatbotPayload
from src.schemas.outputparser import ResponseOutputParser
from src.types.documents import RetrievedDocument
from src.types.executions import ExecutionType
from typing import Literal
from typing import NotRequired
from typing import Required
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


class State(TypedDict):
    """
    Defines the internal state structure for a chatbot interaction.
    """
    sessionId: str
    exchangeId: str
    recentInteractions: list[tuple[str, str]]
    memoryText: str
    rewrittenQuery: str
    language: str
    context: str
    retrievedDocuments: NotRequired[list[RetrievedDocument]]
    message: str
    response: (ResponseOutputParser | None)
    execution: list[Execution]


# --- OUTPUT ---
class AnswerMetadata(TypedDict):
    """
    Answered/category metadata derived for an assistant response.
    """
    answered: bool
    category: str


class ChatbotResult(TypedDict):
    """
    Final chatbot response returned to the client.
    """
    response: str
    exchangeId: NotRequired[str]


StreamEventType = Literal[
    'ready',        # stream accepted, generation started
    'token',        # next chunk of the answer
    'stream_end',   # no more tokens
    'done',         # terminal event, carries the answer metadata
    'error',        # generation failed, the stream ends here
]


StreamErrorCode = Literal[
    'timeout',      # the model took too long
    'rate_limit',   # the provider throttled us
    'auth',         # the provider rejected our credentials
    'unavailable',  # the provider or a dependency is down
    'unknown',      # anything the table does not recognize
]


class StreamEvent(TypedDict, total=False):
    """
    Base type for all stream events.
    """
    type: Required[StreamEventType]
    content: str
    sessionId: str
    answered: bool
    category: str
    exchangeId: str
    error_code: StreamErrorCode
    message: str


# --- CACHE ---
class CachedResponse(TypedDict):
    """
    Cached assistant response, keyed by normalized query.
    """
    response: str
    answered: bool
    category: str
