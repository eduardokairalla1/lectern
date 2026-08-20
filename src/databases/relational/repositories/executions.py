"""
Executions table repository.
"""

# --- IMPORTS ---
from sqlalchemy.exc import IntegrityError
from src.databases.relational.models.executions import Executions
from src.databases.relational.setup.base_repository import BaseRepository
from src.errors.already_exists_error import AlreadyExistsError


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

