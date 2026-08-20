"""
Exchanges table repository.
"""

# --- IMPORTS ---
from sqlalchemy.exc import IntegrityError
from src.databases.relational.models.exchanges import Exchanges
from src.databases.relational.setup.base_repository import BaseRepository
from src.errors.already_exists_error import AlreadyExistsError


# --- CODE ---
class ExchangesRepository(BaseRepository):
    """
    Repository responsible for operations related to the exchanges table.
    """

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

