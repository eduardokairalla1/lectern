"""
Session feedback table repository.
"""

# --- IMPORTS ---
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.databases.relational.models.session_feedback import SessionFeedback
from src.databases.relational.models.sessions import Sessions
from src.databases.relational.setup.base_repository import BaseRepository


# --- CODE ---
class SessionFeedbackRepository(BaseRepository):
    """
    Repository responsible for operations related to session feedback.
    """

    async def upsert_session_feedback(
        self,
        session_id: str,
        score: int,
        comment: str | None = None,
    ) -> None:
        """
        Records a rating of the conversation at its current depth.

        :param session_id: Client session identifier.
        :param score: Visitor rating of the conversation, from 0 to 10.
        :param comment: Optional free-text note.

        :returns: None.
        """
        # open database connection
        async with self._session() as session:

            # get the current depth of the conversation
            depth = (
                select(Sessions.message_count)
                .where(Sessions.id == session_id)
                .scalar_subquery()
            )

            # insert or update the session feedback record
            stmt = pg_insert(SessionFeedback).values(
                session_id=session_id,
                score=score,
                comment=comment,
                message_count=depth,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[
                    SessionFeedback.session_id,
                    SessionFeedback.message_count,
                ],
                set_={
                    'score': stmt.excluded.score,
                    'comment': stmt.excluded.comment,
                    'updated_at': text('NOW()'),
                },
            )
            await session.execute(stmt)

            # commit changes
            await session.commit()

