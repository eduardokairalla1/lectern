"""
Exchanges model.
"""

# --- IMPORTS ---
from datetime import datetime
from sqlalchemy import Computed
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import func
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from src.databases.relational.setup.base import BASE
from typing import TYPE_CHECKING
from typing import Optional

import uuid


if TYPE_CHECKING:
    from src.databases.relational.models.exchange_feedback import (
        ExchangeFeedback,
    )
    from src.databases.relational.models.executions import Executions
    from src.databases.relational.models.sessions import Sessions


# --- CODE ---
class Exchanges(BASE):
    """
    Defines the exchanges entity.
    """

    __tablename__ = 'exchanges'

    # primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        comment='Unique identifier for the exchange',
    )

    # exchange data
    session_id: Mapped[str] = mapped_column(
        ForeignKey('sessions.id', ondelete='CASCADE'),
        comment='Client session identifier',
    )
    user_message: Mapped[str] = mapped_column(comment="User's question/message")
    assistant_response: Mapped[str] = mapped_column(
        comment="AI assistant's response"
    )

    # context and retrieval
    rewritten_query: Mapped[str | None] = mapped_column(
        comment='Query rewritten by LLM for better RAG retrieval'
    )
    retrieved_documents: Mapped[list | None] = mapped_column(
        JSONB, comment='Documents retrieved from Qdrant vector DB'
    )
    memory_summary: Mapped[str | None] = mapped_column(
        comment='Conversation memory summary from Redis'
    )

    # analysis and classification
    was_answered_successfully: Mapped[bool | None] = mapped_column(
        comment='Whether the AI answered adequately'
    )
    topic_category: Mapped[str | None] = mapped_column(
        comment="Topic category (e.g., 'projects', 'contact')"
    )

    # request metadata
    request_ip: Mapped[str | None] = mapped_column(
        comment='IP address of the request'
    )

    # a cached answer costs no LLM call, so it has no executions: without
    # this flag those exchanges would look like free ones in the dashboards
    served_from_cache: Mapped[bool] = mapped_column(
        server_default=text('false'),
        comment='Whether the answer was served from the response cache',
    )

    # full-text search: generated column over the message pair, GIN-indexed
    search_tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('portuguese', coalesce(user_message, '') "
            "|| ' ' || coalesce(assistant_response, ''))",
            persisted=True,
        ),
        comment='Full-text search vector (user_message + assistant_response)',
    )

    # timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text('NOW()'),
        index=True,
        comment='Timestamp of the exchange',
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text('NOW()'),
        onupdate=func.now(),
        comment='Timestamp of the latest update (e.g., reclassification)',
    )

    # relationships
    executions: Mapped[list['Executions']] = relationship(
        back_populates='exchange',
        cascade='all, delete-orphan',
        order_by='Executions.created_at',
    )
    session: Mapped['Sessions'] = relationship(back_populates='exchanges')
    feedback: Mapped[Optional['ExchangeFeedback']] = relationship(
        back_populates='exchange',
        uselist=False,
        cascade='all, delete-orphan',
    )

    # composite indexes for analytics
    __table_args__ = (
        Index('idx_exchanges_session_created', 'session_id', 'created_at'),
        Index(
            'idx_exchanges_topic_success',
            'topic_category',
            'was_answered_successfully',
        ),
        # Dashboard: cache-hit rate over time
        Index('idx_exchanges_cache_created', 'served_from_cache',
              'created_at'),
        # Dashboard: list unanswered questions (newest first)
        Index(
            'idx_exchanges_unanswered',
            'created_at',
            postgresql_where=text('was_answered_successfully = false'),
        ),
        # Dashboard: full-text search over the exchange text
        Index('idx_exchanges_search', 'search_tsv', postgresql_using='gin'),
    )

    def __repr__(self) -> str:
        """
        Readable representation, for logs and debugging.

        :return: The debug representation of the row.
        """
        return (
            f'<Exchange(id={self.id}, session={self.session_id[:8]}, '
            f'created={self.created_at})>'
        )
