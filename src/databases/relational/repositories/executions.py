"""
Executions table repository.
"""

# --- IMPORTS ---
from sqlalchemy import desc
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.databases.relational.models.executions import Executions
from src.databases.relational.setup.base_repository import BaseRepository
from src.errors.already_exists_error import AlreadyExistsError
from src.types.stats import TokenUsageByModel
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


    async def list_executions(
        self,
        execution_type: str | None = None,
        llm_model: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Executions]:
        """
        List executions with optional filters.

        :param execution_type: Filter by execution type (optional).
        :param llm_model: Filter by LLM model (optional).
        :param limit: Maximum number of results (default: 100).
        :param offset: Number of results to skip (default: 0).

        :returns: List of executions.
        """
        # open database connection
        async with self._session() as session:

            # build query
            stmt = select(Executions)

            # execution type filter is provided: apply it
            if execution_type is not None:
                stmt = stmt.where(
                    Executions.execution_type == execution_type
                )

            # llm model filter is provided: apply it
            if llm_model is not None:
                stmt = stmt.where(Executions.llm_model == llm_model)

            # order by most recent and apply pagination
            stmt = (
                stmt.order_by(desc(Executions.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await session.execute(stmt)

            # returns list of executions
            return list(result.scalars().all())


    async def get_total_tokens_by_model(self) -> list[TokenUsageByModel]:
        """
        Get aggregated token usage grouped by LLM model.

        :returns: List of dictionaries with model and total tokens.
        """
        # open database connection
        async with self._session() as session:

            # query aggregated data
            stmt = (
                select(
                    Executions.llm_model,
                    func.sum(Executions.total_tokens).label('total_tokens'),
                    func.count(Executions.id).label('execution_count'),
                    func.avg(Executions.total_duration_ms).label(
                        'avg_duration_ms'
                    ),
                )
                .where(Executions.llm_model.isnot(None))
                .group_by(Executions.llm_model)
            )

            result = await session.execute(stmt)

            # format results as list of dictionaries
            return [
                {
                    'llm_model': row.llm_model,
                    'total_tokens': int(row.total_tokens)
                    if row.total_tokens
                    else 0,
                    'execution_count': row.execution_count,
                    'avg_duration_ms': float(row.avg_duration_ms)
                    if row.avg_duration_ms
                    else 0.0,
                }
                for row in result.all()
            ]


    async def delete_execution(self, execution_id: UUID) -> None:
        """
        Delete an execution by id.

        :param execution_id: UUID of the execution.

        :returns: None.
        """
        # open database connection
        async with self._session() as session:

            # delete execution from database
            stmt = select(Executions).where(Executions.id == execution_id)
            result = await session.execute(stmt)
            execution = result.scalar_one_or_none()

            # execution exists: delete it
            if execution:
                await session.delete(execution)
                await session.commit()
