"""
Exchanges table repository.
"""

# --- IMPORTS ---
from sqlalchemy import desc
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.databases.relational.models.exchanges import Exchanges
from src.databases.relational.setup.base_repository import BaseRepository
from src.errors.already_exists_error import AlreadyExistsError
from uuid import UUID


# --- CODE ---
class ExchangesRepository(BaseRepository):
    """
    Repository responsible for operations related to the exchanges table.
    """

    @staticmethod
    async def _get(
        session: AsyncSession, exchange_id: UUID
    ) -> Exchanges | None:
        """
        Loads an exchange into the caller's session, so it can be mutated
        or deleted within the same transaction.

        :param session: The active database session.
        :param exchange_id: UUID of the exchange.

        :returns: Exchange or None if not found.
        """
        stmt = select(Exchanges).where(Exchanges.id == exchange_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def insert_exchange(self, exchange: Exchanges) -> Exchanges:
        """
        Insert a new exchange to database.

        :param exchange: Exchange model instance.

        :returns: Persisted exchange with updated fields.
        """
        # open database connection
        async with self._session() as session:

            # insert exchange to database
            try:
                session.add(exchange)

                # commit changes
                await session.commit()

                # return new inserted exchange
                return exchange

            # exchange already exists: raise error
            except IntegrityError as e:
                self._logger.warning(
                    'Duplicate exchange insert attempt (session=%s)',
                    exchange.session_id,
                )
                raise AlreadyExistsError(
                    {
                        'entity': 'exchange',
                        'local': 'database',
                        'detail': 'Exchange already exists.',
                    }
                ) from e


    async def get_by_id(self, exchange_id: UUID) -> Exchanges | None:
        """
        Retrieves an exchange by id.

        :param exchange_id: UUID of the exchange.

        :returns: Exchange or None if not found.
        """
        # open database connection
        async with self._session() as session:

            # returns Exchange or None
            return await self._get(session, exchange_id)


    async def get_by_session_id(
        self, session_id: str, limit: int = 50, offset: int = 0
    ) -> list[Exchanges]:
        """
        Retrieves all exchanges for a specific session.

        :param session_id: Session identifier.
        :param limit: Maximum number of results (default: 50).
        :param offset: Number of results to skip (default: 0).

        :returns: List of exchanges.
        """
        # open database connection
        async with self._session() as session:

            # retrieves exchanges by session_id from database
            stmt = (
                select(Exchanges)
                .where(Exchanges.session_id == session_id)
                .order_by(desc(Exchanges.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await session.execute(stmt)

            # returns list of exchanges
            return list(result.scalars().all())


    async def list_exchanges(
        self,
        topic_category: str | None = None,
        was_answered_successfully: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Exchanges]:
        """
        List exchanges with optional filters.

        :param topic_category: Filter by topic category (optional).
        :param was_answered_successfully: Filter by answer success (optional).
        :param limit: Maximum number of results (default: 100).
        :param offset: Number of results to skip (default: 0).

        :returns: List of exchanges.
        """
        # open database connection
        async with self._session() as session:

            # build query
            stmt = select(Exchanges)

            # topic category filter is provided: apply it
            if topic_category is not None:
                stmt = stmt.where(
                    Exchanges.topic_category == topic_category
                )

            # was answered successfully filter is provided: apply it
            if was_answered_successfully is not None:
                stmt = stmt.where(
                    Exchanges.was_answered_successfully
                    == was_answered_successfully
                )

            # order by most recent and apply pagination
            stmt = (
                stmt.order_by(desc(Exchanges.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await session.execute(stmt)

            # returns list of exchanges
            return list(result.scalars().all())

    async def search_exchanges(
        self, query: str, limit: int = 50
    ) -> list[Exchanges]:
        """
        Full-text search over the exchange text (user message + assistant
        response), using the GIN-indexed search_tsv generated column.

        :param query: Free-text search terms.
        :param limit: Maximum number of results.

        :returns: Matching exchanges, newest first.
        """
        # open database connection
        async with self._session() as session:

            # match the tsvector column against the user's terms
            stmt = (
                select(Exchanges)
                .where(
                    Exchanges.search_tsv.op('@@')(
                        func.plainto_tsquery('portuguese', query)
                    )
                )
                .order_by(desc(Exchanges.created_at))
                .limit(limit)
            )

            result = await session.execute(stmt)

            # returns list of matching exchanges
            return list(result.scalars().all())

