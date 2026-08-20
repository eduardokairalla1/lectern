"""
Sessions model.
"""

# --- IMPORTS ---
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy import text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from src.databases.relational.setup.base import BASE
from typing import TYPE_CHECKING
from typing import Optional


if TYPE_CHECKING:
    from src.databases.relational.models.exchanges import Exchanges
    from src.databases.relational.models.session_feedback import SessionFeedback


# --- CODE ---
class Sessions(BASE):
    """
    Defines the sessions entity.
    """

    __tablename__ = 'sessions'

    # primary key: the client session identifier (validated slug, 10-50 chars)
    id: Mapped[str] = mapped_column(
        primary_key=True, comment='Client session identifier'
    )

    # visit window
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text('NOW()'),
        comment="Timestamp of the session's first message",
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text('NOW()'),
        index=True,
        comment="Timestamp of the session's most recent message",
    )

    # client metadata (latest seen values)
    request_ip: Mapped[str | None] = mapped_column(
        comment='IP address of the visitor'
    )
    user_agent: Mapped[str | None] = mapped_column(
        comment="User agent of the visitor's browser"
    )

    # counters
    message_count: Mapped[int] = mapped_column(
        server_default=text('0'),
        comment='Number of exchanges in this session',
    )

    # relationships
    exchanges: Mapped[list['Exchanges']] = relationship(
        back_populates='session',
        cascade='all, delete-orphan',
        order_by='Exchanges.created_at',
    )
    feedback: Mapped[Optional['SessionFeedback']] = relationship(
        back_populates='session',
        uselist=False,
        cascade='all, delete-orphan',
    )

    def __repr__(self) -> str:
        """
        Readable representation, for logs and debugging.

        :return: The debug representation of the row.
        """
        return (
            f'<Session(id={self.id[:8]}, messages={self.message_count}, '
            f'last_seen={self.last_seen})>'
        )
