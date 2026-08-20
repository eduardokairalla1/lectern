"""
Chatbot endpoints.
"""

# --- IMPORTS ---
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from src.dependencies.auth import verify_api_key
from src.dependencies.client_info import get_client_ip
from src.errors.database_unavailable_error import DatabaseUnavailableError
from src.errors.invalid_request_error import InvalidRequestError
from src.errors.payload_too_large_error import PayloadTooLargeError
from src.errors.processing_error import ProcessingError
from src.errors.redis_unavailable_error import RedisUnavailableError
from src.errors.transcription_error import TranscriptionError
from src.errors.unauthorized_error import UnauthorizedError
from src.errors.unsupported_media_type_error import UnsupportedMediaTypeError
from src.errors.vector_store_unavailable_error import (
    VectorStoreUnavailableError,
)
from src.schemas.endpoints.chatbot_response import ChatbotPayload
from src.schemas.endpoints.chatbot_response import ChatbotResponse
from src.schemas.errors import VALIDATION_RESPONSE
from src.schemas.errors import error_responses
from src.services.chatbot.respond import respond
from src.services.chatbot.types import ChatbotResult
from src.services.chatbot.types import ChatMessage


# --- GLOBAL ---
router = APIRouter()

# built-in error responses
ANSWER_ERRORS = {
    **error_responses(
        InvalidRequestError,
        UnauthorizedError,
        PayloadTooLargeError,
        UnsupportedMediaTypeError,
        TranscriptionError,
        ProcessingError,
        VectorStoreUnavailableError,
        RedisUnavailableError,
        DatabaseUnavailableError,
    ),
    **VALIDATION_RESPONSE,
}


# --- CODE ---
@router.post('/response',
             summary='Ask a question and get the full answer',
             response_model=ChatbotResponse,
             response_model_exclude_none=True,
             responses=ANSWER_ERRORS,
             dependencies=[Depends(verify_api_key)])
async def chatbot_endpoint(
    request: Request,
    payload: ChatbotPayload,
) -> ChatbotResult:
    """
    Answers a question about the subject, in a single JSON document.

    The message may be text or base64 audio; audio is transcribed first. The
    answer is grounded on the retrieved documents: when nothing relevant is
    found, the assistant says so rather than inventing an answer.

    `exchangeId` identifies this question/answer pair and is what
    `POST /api/chatbot/feedback/exchange/{exchangeId}` rates. It is always
    present, including when the answer came from cache: a cached answer is
    still an exchange, and it can still be rated.

    Prefer `/api/chatbot/response/stream` when you want to render tokens as they
    are produced.
    """
    return await respond(
        ChatMessage.from_payload(payload),
        request_ip=get_client_ip(request),
        user_agent=request.headers.get('user-agent'),
    )


