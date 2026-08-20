"""
Exchange feedback model.
"""

# --- IMPORTS ---
from datetime import datetime
from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import func
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from src.databases.relational.setup.base import BASE
from typing import TYPE_CHECKING

import uuid


if TYPE_CHECKING:
    from src.databases.relational.models.exchanges import Exchanges


# --- CODE ---
class ExchangeFeedback(BASE):
    """
    Defines the feedback entity.
    """

    __tablename__ = 'exchange_feedback'

    # primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        comment='Unique identifier for the feedback',
    )

    # foreign key: one feedback per exchange
    exchange_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('exchanges.id', ondelete='CASCADE'),
        unique=True,
        index=True,
        comment='Reference to the rated exchange',
    )

    # rating data
    rating: Mapped[str] = mapped_column(
        comment="Visitor rating: 'up' or 'down'"
    )
    comment: Mapped[str | None] = mapped_column(
        comment='Optional free-text comment'
    )

    # timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text('NOW()'),
        comment='Timestamp when feedback was first given',
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text('NOW()'),
        onupdate=func.now(),
        comment='Timestamp of the latest feedback update',
    )

    # relationships
    exchange: Mapped['Exchanges'] = relationship(
        back_populates='feedback'
    )

    # constraints
    __table_args__ = (
        CheckConstraint(
            "rating IN ('up', 'down')",
            name='ck_exchange_feedback_rating',
        ),
    )

    def __repr__(self) -> str:
        """
        Readable representation, for logs and debugging.

        :return: The debug representation of the row.
        """
        return (
            f'<ExchangeFeedback(id={self.id}, exchange={self.exchange_id}, '
            f'rating={self.rating})>'
        )
