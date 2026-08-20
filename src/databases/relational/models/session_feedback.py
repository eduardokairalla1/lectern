"""
Session feedback model.
"""

# --- IMPORTS ---
from datetime import datetime
from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
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
    from src.databases.relational.models.sessions import Sessions


# --- CODE ---
class SessionFeedback(BASE):
    """
    Defines the session feedback entity.
    Stores the visitor's rating of a whole conversation (0-10) plus an
    optional written note. A session may collect SEVERAL, one per depth it
    was rated at: a conversation keeps growing, so a rating given after
    three exchanges and one given after nine are about different amounts of
    conversation, and keeping only the last would erase the trajectory.

    Different from ExchangeFeedback, which rates a single answer: that one
    is capped at one row because an exchange is immutable, so a second
    rating of it is a change of mind rather than new information.
    """

    __tablename__ = 'session_feedback'

    # primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        comment='Unique identifier for the session feedback',
    )

    # foreign key: several ratings per session, one per depth
    session_id: Mapped[str] = mapped_column(
        ForeignKey('sessions.id', ondelete='CASCADE'),
        index=True,
        comment='Reference to the rated session',
    )

    # rating data
    score: Mapped[int] = mapped_column(
        comment='Visitor rating of the conversation, from 0 to 10'
    )
    comment: Mapped[str | None] = mapped_column(
        comment='Optional free-text note'
    )

    # how deep into the conversation the visitor rated, captured at write
    # time because sessions.message_count keeps growing afterwards. Part of
    # the uniqueness key, so it can never be null
    message_count: Mapped[int] = mapped_column(
        comment='Number of exchanges the session had when it was rated'
    )

    # timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text('NOW()'),
        index=True,
        comment='Timestamp when the rating was first given',
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text('NOW()'),
        onupdate=func.now(),
        comment='Timestamp of the latest rating update',
    )

    # relationships
    session: Mapped['Sessions'] = relationship(back_populates='feedback')

    # constraints: one rating per depth. Rating again without sending a
    # new message is the same opinion and updates; rating after the
    # conversation grew is new information and inserts another row.
    __table_args__ = (
        CheckConstraint(
            'score >= 0 AND score <= 10', name='ck_session_feedback_score'
        ),
        UniqueConstraint(
            'session_id',
            'message_count',
            name='uq_session_feedback_session_depth',
        ),
    )

    def __repr__(self) -> str:
        """
        Readable representation, for logs and debugging.

        :return: The debug representation of the row.
        """
        return (
            f'<SessionFeedback(id={self.id}, session={self.session_id[:8]}, '
            f'score={self.score})>'
        )
