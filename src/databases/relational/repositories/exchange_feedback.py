"""
Exchange feedback table repository.
"""

# --- IMPORTS ---
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.databases.relational.models.exchange_feedback import ExchangeFeedback
from src.databases.relational.setup.base_repository import BaseRepository
from uuid import UUID


# --- CODE ---
class ExchangeFeedbackRepository(BaseRepository):
    """
    Repository responsible for operations related to the feedback table.
    """

    async def upsert_feedback(
        self,
        exchange_id: UUID,
        rating: str,
        comment: str | None = None,
    ) -> None:
        """
        Inserts the feedback for an exchange or, when one already exists,
        updates it (the visitor changed their rating/comment).

        :param exchange_id: UUID of the rated exchange.
        :param rating: Visitor rating: 'up' or 'down'.
        :param comment: Optional free-text comment.

        :returns: None.
        """
        # open database connection
        async with self._session() as session:

            # insert or update the feedback record
            stmt = pg_insert(ExchangeFeedback).values(
                exchange_id=exchange_id,
                rating=rating,
                comment=comment,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[ExchangeFeedback.exchange_id],
                set_={
                    'rating': stmt.excluded.rating,
                    'comment': stmt.excluded.comment,
                    'updated_at': text('NOW()'),
                },
            )
            await session.execute(stmt)

            # Commit changes
            await session.commit()

