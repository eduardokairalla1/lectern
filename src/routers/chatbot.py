"""
Chatbot endpoints.
"""

# --- IMPORTS ---
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.responses import StreamingResponse
from src.dependencies.auth import verify_api_key
from src.dependencies.client_info import get_client_ip
from src.dependencies.identifiers import valid_exchange_id
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
from src.schemas.endpoints.chatbot_feedback import FeedbackPayload
from src.schemas.endpoints.chatbot_feedback import FeedbackResponse
from src.schemas.endpoints.chatbot_response import ChatbotPayload
from src.schemas.endpoints.chatbot_response import ChatbotResponse
from src.schemas.errors import VALIDATION_RESPONSE
from src.schemas.errors import error_responses
from src.services.chatbot.persistence import schedule_feedback
from src.services.chatbot.respond import respond
from src.services.chatbot.respond_stream import respond_stream
from src.services.chatbot.types import ChatbotResult
from src.services.chatbot.types import ChatMessage
from typing import Annotated


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


@router.post('/response/stream',
             summary='Ask a question and stream the answer (SSE)',
             dependencies=[Depends(verify_api_key)],
             response_class=StreamingResponse,
             responses={
                 200: {
                     'description': 'Server-sent event stream of the answer.',
                     'content': {'text/event-stream': {}},
                 },
                 **ANSWER_ERRORS,
             })
async def chatbot_stream_endpoint(
    request: Request,
    payload: ChatbotPayload,
) -> StreamingResponse:
    """
    Answers a question about the subject, streaming tokens as they are produced.

    Same input and same answer as `POST /api/chatbot/response`, delivered as
    server-sent events. Each frame is `data: <json>\\n\\n`, and every event
    carries a `type`:

    | `type` | payload | meaning |
    | --- | --- | --- |
    | `ready` | `sessionId` | stream accepted, generation started |
    | `token` | `content` | next chunk of the answer, append it as-is |
    | `stream_end` | — | no more tokens |
    | `done` | `answered`, `category`, `exchangeId` | terminal event |
    | `error` | `error_code`, `message` | generation failed, stream ends |

    Consume until `done` or `error`; only one of them is ever sent. As in the
    JSON endpoint, `done` always carries an `exchangeId`, cache hits
    included.

    Errors raised **before** the stream starts (authentication, validation,
    transcription) are returned as a regular JSON error response with the
    status codes listed below. Once the stream is open the status is already
    `200`, so later failures arrive as an `error` event instead — its
    `error_code` is one of `timeout`, `rate_limit`, `auth`, `unavailable` or
    `unknown`.

    Token text is HTML-escaped, so it can be rendered without further
    sanitizing.
    """
    generator = await respond_stream(
        ChatMessage.from_payload(payload),
        request_ip=get_client_ip(request),
        user_agent=request.headers.get('user-agent'),
    )

    return StreamingResponse(
        generator,
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@router.post('/feedback/exchange/{exchangeId}',
             summary='Rate an answer',
             status_code=202,
             response_model=FeedbackResponse,
             responses={
                 **error_responses(
                     InvalidRequestError,
                     UnauthorizedError,
                     ProcessingError,
                 ),
                 **VALIDATION_RESPONSE,
             },
             dependencies=[Depends(verify_api_key)])
async def chatbot_feedback_endpoint(
    exchange_id: Annotated[str, Depends(valid_exchange_id)],
    payload: FeedbackPayload,
) -> FeedbackResponse:
    """
    Records a visitor's rating of one previous answer.

    The exchange is the one the answer returned. Rates a single answer; use
    `POST /api/chatbot/feedback/session/{sessionId}` to rate the conversation
    as a whole. The two are independent, and a client may send either, both,
    or neither.

    Sending feedback twice for the same exchange updates the previous rating
    instead of adding a second one.

    Responds `202 Accepted`: the rating is persisted by a background worker,
    so a successful response means it was accepted, not yet stored.
    """
    schedule_feedback(
        exchange_id=exchange_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    return FeedbackResponse(status='accepted')


