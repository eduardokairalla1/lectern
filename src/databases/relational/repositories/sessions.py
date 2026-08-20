"""
Sessions table repository.
"""

# --- IMPORTS ---
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.databases.relational.models.sessions import Sessions
from src.databases.relational.setup.base_repository import BaseRepository


# --- CODE ---
class SessionsRepository(BaseRepository):
    """
    Repository responsible for operations related to the sessions table.
    """

    async def upsert_session(
        self,
        session_id: str,
        request_ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Inserts a session or, when it already exists, refreshes last_seen,
        the client metadata and increments the message counter.

        :param session_id: Client session identifier.
        :param request_ip: IP address of the visitor (optional).
        :param user_agent: User agent of the visitor's browser (optional).

        :returns: None.
        """
        # open database connection
        async with self._session() as session:

            # insert or update the session record
            stmt = pg_insert(Sessions).values(
                id=session_id,
                request_ip=request_ip,
                user_agent=user_agent,
                message_count=1,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[Sessions.id],
                set_={
                    'last_seen': text('NOW()'),
                    'request_ip': stmt.excluded.request_ip,
                    'user_agent': stmt.excluded.user_agent,
                    'message_count': Sessions.message_count + 1,
                },
            )
            await session.execute(stmt)

            # commit changes
            await session.commit()
