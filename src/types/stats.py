"""
Stats types for exchange tracking.
"""

# --- IMPORTS ---
from src.types.documents import RetrievedDocument
from src.types.executions import ExecutionType
from typing import TypedDict
from uuid import UUID


# --- CODE ---
class SessionStats(TypedDict, total=False):
    """
    Stats for sessions.
    """
    id: str
    request_ip: str | None
    user_agent: str | None


class ExchangeStats(TypedDict, total=False):
    """
    Stats for exchanges.
    """
    id: str | UUID
    session_id: str
    user_message: str
    assistant_response: str
    rewritten_query: str | None
    retrieved_documents: list[RetrievedDocument] | None
    memory_summary: str | None
    was_answered_successfully: bool | None
    topic_category: str | None
    request_ip: str | None
    served_from_cache: bool


class ExecutionStats(TypedDict, total=False):
    """
    Stats for execution.
    """
    execution_type: ExecutionType
    llm_model: str | None
    embedding_model: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    total_duration_ms: int | None


class TokenUsageByModel(TypedDict):
    """
    Aggregated token usage for a single LLM model.
    """
    llm_model: str
    total_tokens: int
    execution_count: int
    avg_duration_ms: float
