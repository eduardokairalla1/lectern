"""
Executions model.
"""

# --- IMPORTS ---
from datetime import datetime
from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from src.databases.relational.setup.base import BASE
from src.types.executions import EXECUTION_TYPE_PATTERN
from typing import TYPE_CHECKING

import uuid


if TYPE_CHECKING:
    from src.databases.relational.models.exchanges import Exchanges


# --- CODE ---
class Executions(BASE):
    """
    Defines the executions entity.
    """

    __tablename__ = 'executions'

    # primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        comment='Unique identifier for the execution',
    )

    # foreign key
    exchange_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('exchanges.id', ondelete='CASCADE'),
        index=True,
        comment='Reference to the exchange',
    )

    # execution type
    execution_type: Mapped[str] = mapped_column(
        comment="Type of execution (e.g., 'chatbot_answer', 'query_rewrite')"
    )

    # models used
    llm_model: Mapped[str | None] = mapped_column(
        comment="LLM model used (e.g., 'gpt-4o-mini')"
    )
    embedding_model: Mapped[str | None] = mapped_column(
        comment='Embedding model used'
    )

    # token usage
    input_tokens: Mapped[int | None] = mapped_column(
        comment='Number of input tokens'
    )
    output_tokens: Mapped[int | None] = mapped_column(
        comment='Number of output tokens'
    )
    total_tokens: Mapped[int | None] = mapped_column(
        comment='Total tokens used'
    )

    # performance metrics
    total_duration_ms: Mapped[int | None] = mapped_column(
        comment='Total execution duration in milliseconds'
    )

    # timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text('NOW()'),
        index=True,
        comment='Timestamp of execution',
    )

    # relationships
    exchange: Mapped['Exchanges'] = relationship(
        back_populates='executions'
    )

    # table args
    __table_args__ = (
        Index('idx_executions_model_created', 'llm_model', 'created_at'),
        Index('idx_executions_type_created', 'execution_type', 'created_at'),
        CheckConstraint(
            'coalesce(input_tokens, 0) >= 0 '
            'AND coalesce(output_tokens, 0) >= 0 '
            'AND coalesce(total_tokens, 0) >= 0',
            name='ck_executions_tokens_positive',
        ),
        CheckConstraint(
            f"execution_type ~ '{EXECUTION_TYPE_PATTERN}'",
            name='ck_executions_type',
        ),
    )

    def __repr__(self) -> str:
        """
        Readable representation, for logs and debugging.

        :return: The debug representation of the row.
        """
        return (
            f'<Execution(id={self.id}, type={self.execution_type}, '
            f'tokens={self.total_tokens})>'
        )
