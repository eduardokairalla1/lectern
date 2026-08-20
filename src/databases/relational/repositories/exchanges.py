"""
Exchanges table repository.
"""

# --- IMPORTS ---
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

