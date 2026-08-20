"""
Executions table repository.
"""

# --- IMPORTS ---
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.databases.relational.models.executions import Executions
from src.databases.relational.setup.base_repository import BaseRepository
from src.errors.already_exists_error import AlreadyExistsError
from uuid import UUID


# --- CODE ---
class ExecutionsRepository(BaseRepository):
    """
    Repository responsible for operations related to the executions table.
    """

    async def insert_executions(self, executions: list[Executions]) -> None:
        """
        Insert the executions of an exchange to database, in a single
        transaction.

        :param executions: Execution model instances.

        :returns: None.
        """
        # nothing to insert: skip the transaction entirely
        if not executions:
            return

        # open database connection
        async with self._session() as session:
            try:
                # Insert executions to database
                session.add_all(executions)

                # Commit changes
                await session.commit()

            # an execution already exists: raise error
            except IntegrityError as e:
                self._logger.warning(
                    'Duplicate execution insert attempt (exchange=%s)',
                    executions[0].exchange_id,
                )
                raise AlreadyExistsError(
                    {
                        'entity': 'execution',
                        'local': 'database',
                        'detail': 'Execution already exists.',
                    }
                ) from e


    async def get_by_id(self, execution_id: UUID) -> Executions | None:
        """
        Retrieves an execution by id.

        :param execution_id: UUID of the execution.

        :returns: Execution or None if not found.
        """
        # open database connection
        async with self._session() as session:

            # retrieve execution by id from database
            stmt = select(Executions).where(Executions.id == execution_id)
            result = await session.execute(stmt)

            # returns Execution or None
            return result.scalar_one_or_none()


    async def get_by_exchange_id(
        self, exchange_id: UUID
    ) -> list[Executions]:
        """
        Retrieves every execution of an exchange (an exchange has several:
        query rewrite, answer, metadata extraction), in chronological order.

        :param exchange_id: UUID of the exchange.

        :returns: List of executions (empty when none exist).
        """
        # open database connection
        async with self._session() as session:

            # retrieves executions by exchange_id from database
            stmt = (
                select(Executions)
                .where(Executions.exchange_id == exchange_id)
                .order_by(Executions.created_at)
            )
            result = await session.execute(stmt)

            # returns list of executions (empty when none exist)
            return list(result.scalars().all())

