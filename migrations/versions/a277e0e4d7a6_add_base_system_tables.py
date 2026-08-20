"""
Add base system tables

Revision ID: a277e0e4d7a6
Revises:
Create Date: 2026-07-18 12:32:19.871164
"""

# --- IMPORTS ---
from alembic import op
from sqlalchemy.dialects import postgresql
from typing import Sequence
from typing import Union

import sqlalchemy as sa


# --- GLOBALS ---
revision: str = 'a277e0e4d7a6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- CODE ---
def upgrade() -> None:
    """
    Upgrade schema.

    :return: None
    """

    # session table
    op.create_table(
        'sessions',
        sa.Column('id', sa.TEXT(),
                nullable=False,
                comment='Client session identifier'),
        sa.Column('first_seen',
                sa.DateTime(timezone=True),
                server_default=sa.text('NOW()'),
                nullable=False,
                comment="Timestamp of the session's first message"),
        sa.Column('last_seen',
                sa.DateTime(timezone=True),
                server_default=sa.text('NOW()'),
                nullable=False,
                comment="Timestamp of the session's most recent message"),
        sa.Column('request_ip',
                sa.TEXT(),
                nullable=True,
                comment='IP address of the visitor'),
        sa.Column('user_agent',
                sa.TEXT(),
                nullable=True,
                comment="User agent of the visitor's browser"),
        sa.Column('message_count',
                sa.Integer(),
                server_default=sa.text('0'),
                nullable=False,
                comment='Number of exchanges in this session'),
        sa.PrimaryKeyConstraint('id')
    )

    # index for last_seen
    op.create_index(op.f('ix_sessions_last_seen'),
                    'sessions',
                    ['last_seen'],
                    unique=False)

    # exchange table
    op.create_table(
        'exchanges',
        sa.Column('id', sa.UUID(),
                server_default=sa.text('gen_random_uuid()'),
                nullable=False,
                comment='Unique identifier for the exchange'),
        sa.Column('session_id',
                sa.TEXT(),
                nullable=False,
                comment='Client session identifier'),
        sa.Column('user_message',
                sa.TEXT(),
                nullable=False,
                comment="User's question/message"),
        sa.Column('assistant_response',
                sa.TEXT(),
                nullable=False,
                comment="AI assistant's response"),
        sa.Column('rewritten_query',
                sa.TEXT(),
                nullable=True,
                comment='Query rewritten by LLM for better RAG retrieval'),
        sa.Column('retrieved_documents',
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
                comment='Documents retrieved from Qdrant vector DB'),
        sa.Column('memory_summary',
                sa.TEXT(),
                nullable=True,
                comment='Conversation memory summary from Redis'),
        sa.Column('was_answered_successfully',
                sa.Boolean(),
                nullable=True,
                comment='Whether the AI answered adequately'),
        sa.Column('topic_category',
                sa.TEXT(),
                nullable=True,
                comment="Topic category (e.g., 'projects', 'contact')"),
        sa.Column('request_ip',
                sa.TEXT(),
                nullable=True,
                comment='IP address of the request'),
        sa.Column('served_from_cache',
                sa.Boolean(),
                server_default=sa.text('false'),
                nullable=False,
                comment=(
                    'Whether the answer was served from the response cache'
                )),
        sa.Column(
            'search_tsv',
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('portuguese', coalesce(user_message, "
                "'') || ' ' || coalesce(assistant_response, ''))",
                persisted=True,
            ),
            nullable=True,
            comment=(
                'Full-text search vector (user_message + '
                'assistant_response)'
            ),
        ),
        sa.Column('created_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('NOW()'),
                nullable=False,
                comment='Timestamp of the exchange'),
        sa.Column('updated_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('NOW()'),
                nullable=False,
                comment=(
                    'Timestamp of the latest update '
                    '(e.g., reclassification)'
                )),
        sa.ForeignKeyConstraint(['session_id'],
                                ['sessions.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # indexes for exchanges
    op.create_index('idx_exchanges_search',
                    'exchanges',
                    ['search_tsv'],
                    unique=False,
                    postgresql_using='gin')
    op.create_index('idx_exchanges_session_created',
                    'exchanges',
                    ['session_id', 'created_at'],
                    unique=False)
    op.create_index('idx_exchanges_topic_success',
                    'exchanges',
                    ['topic_category', 'was_answered_successfully'],
                    unique=False)
    op.create_index('idx_exchanges_cache_created',
                    'exchanges',
                    ['served_from_cache', 'created_at'],
                    unique=False)
    op.create_index('idx_exchanges_unanswered',
                    'exchanges',
                    ['created_at'],
                    unique=False,
                    postgresql_where=sa.text(
                        'was_answered_successfully = false'
                    ))
    op.create_index(op.f('ix_exchanges_created_at'),
                    'exchanges',
                    ['created_at'],
                    unique=False)

    # execution table
    op.create_table(
        'executions',
        sa.Column('id', sa.UUID(),
                server_default=sa.text('gen_random_uuid()'),
                nullable=False,
                comment='Unique identifier for the execution'),
        sa.Column('exchange_id',
                sa.UUID(),
                nullable=False,
                comment='Reference to the exchange'),
        sa.Column('execution_type',
                sa.TEXT(),
                nullable=False,
                comment=(
                    "Type of execution (e.g., 'chatbot_answer', "
                    "'query_rewrite')"
                )),
        sa.Column('llm_model',
                sa.TEXT(),
                nullable=True,
                comment="LLM model used (e.g., 'gpt-4o-mini')"),
        sa.Column('embedding_model',
                sa.TEXT(),
                nullable=True,
                comment='Embedding model used'),
        sa.Column('input_tokens',
                sa.Integer(),
                nullable=True,
                comment='Number of input tokens'),
        sa.Column('output_tokens',
                sa.Integer(),
                nullable=True,
                comment='Number of output tokens'),
        sa.Column('total_tokens',
                sa.Integer(),
                nullable=True,
                comment='Total tokens used'),
        sa.Column('total_duration_ms',
                sa.Integer(),
                nullable=True,
                comment='Total execution duration in milliseconds'),
        sa.Column('created_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('NOW()'),
                nullable=False,
                comment='Timestamp of execution'),
        sa.CheckConstraint(
            "execution_type ~ "
            "'^(chatbot_answer|query_rewrite|metadata_extraction"
            "|execution_[0-9]+)$'",
            name='ck_executions_type'),
        sa.CheckConstraint(
            'coalesce(input_tokens, 0) >= 0 AND '
            'coalesce(output_tokens, 0) >= 0 AND '
            'coalesce(total_tokens, 0) >= 0',
            name='ck_executions_tokens_positive'),
        sa.ForeignKeyConstraint(['exchange_id'],
                                ['exchanges.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # indexes for executions
    op.create_index('idx_executions_model_created',
                    'executions',
                    ['llm_model', 'created_at'],
                    unique=False)
    op.create_index('idx_executions_type_created',
                    'executions',
                    ['execution_type', 'created_at'],
                    unique=False)
    op.create_index(op.f('ix_executions_exchange_id'),
                    'executions',
                    ['exchange_id'],
                    unique=False)
    op.create_index(op.f('ix_executions_created_at'),
                    'executions',
                    ['created_at'],
                    unique=False)

    # exchange feedback table
    op.create_table(
        'exchange_feedback',
        sa.Column('id', sa.UUID(),
                server_default=sa.text('gen_random_uuid()'),
                nullable=False,
                comment='Unique identifier for the feedback'),
        sa.Column('exchange_id',
                sa.UUID(),
                nullable=False,
                comment='Reference to the rated exchange'),
        sa.Column('rating',
                sa.TEXT(),
                nullable=False,
                comment="Visitor rating: 'up' or 'down'"),
        sa.Column('comment',
                sa.TEXT(),
                nullable=True,
                comment='Optional free-text comment'),
        sa.Column('created_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('NOW()'),
                nullable=False,
                comment='Timestamp when feedback was first given'),
        sa.Column('updated_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('NOW()'),
                nullable=False,
                comment='Timestamp of the latest feedback update'),
        sa.CheckConstraint("rating IN ('up', 'down')",
                        name='ck_exchange_feedback_rating'),
        sa.ForeignKeyConstraint(['exchange_id'],
                                ['exchanges.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # index for exchange_feedback
    op.create_index(op.f('ix_exchange_feedback_exchange_id'),
                    'exchange_feedback',
                    ['exchange_id'],
                    unique=True)

    # session feedback table: one rating of a whole conversation
    op.create_table(
        'session_feedback',
        sa.Column('id', sa.UUID(),
                server_default=sa.text('gen_random_uuid()'),
                nullable=False,
                comment='Unique identifier for the session feedback'),
        sa.Column('session_id',
                sa.TEXT(),
                nullable=False,
                comment='Reference to the rated session'),
        sa.Column('score',
                sa.Integer(),
                nullable=False,
                comment='Visitor rating of the conversation, from 0 to 10'),
        sa.Column('comment',
                sa.TEXT(),
                nullable=True,
                comment='Optional free-text note'),
        sa.Column('message_count',
                sa.Integer(),
                nullable=False,
                comment=(
                    'Number of exchanges the session had when it was rated'
                )),
        sa.Column('created_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('NOW()'),
                nullable=False,
                comment='Timestamp when the rating was first given'),
        sa.Column('updated_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('NOW()'),
                nullable=False,
                comment='Timestamp of the latest rating update'),
        sa.CheckConstraint('score >= 0 AND score <= 10',
                        name='ck_session_feedback_score'),
        sa.ForeignKeyConstraint(['session_id'],
                                ['sessions.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id',
                            'message_count',
                            name='uq_session_feedback_session_depth')
    )

    # indexes for session_feedback
    op.create_index(op.f('ix_session_feedback_session_id'),
                    'session_feedback',
                    ['session_id'],
                    unique=False)
    op.create_index(op.f('ix_session_feedback_created_at'),
                    'session_feedback',
                    ['created_at'],
                    unique=False)


def downgrade() -> None:
    """
    Downgrade schema.

    :return: None
    """

    # drop session_feedback table and indexes
    op.drop_index(op.f('ix_session_feedback_created_at'),
                  table_name='session_feedback')
    op.drop_index(op.f('ix_session_feedback_session_id'),
                  table_name='session_feedback')
    op.drop_table('session_feedback')

    # drop exchange_feedback table and index
    op.drop_index(op.f('ix_exchange_feedback_exchange_id'),
                  table_name='exchange_feedback')
    op.drop_table('exchange_feedback')

    # drop executions table and indexes
    op.drop_index(op.f('ix_executions_created_at'),
                  table_name='executions')
    op.drop_index(op.f('ix_executions_exchange_id'),
                  table_name='executions')
    op.drop_index('idx_executions_type_created',
                  table_name='executions')
    op.drop_index('idx_executions_model_created',
                  table_name='executions')
    op.drop_table('executions')

    # drop exchanges table and indexes
    op.drop_index(op.f('ix_exchanges_created_at'),
                  table_name='exchanges')
    op.drop_index('idx_exchanges_unanswered',
                  table_name='exchanges',
                  postgresql_where=sa.text(
                      'was_answered_successfully = false'))
    op.drop_index('idx_exchanges_cache_created',
                  table_name='exchanges')
    op.drop_index('idx_exchanges_topic_success',
                  table_name='exchanges')
    op.drop_index('idx_exchanges_session_created',
                  table_name='exchanges')
    op.drop_index('idx_exchanges_search',
                  table_name='exchanges',
                  postgresql_using='gin')
    op.drop_table('exchanges')

    # drop sessions table and indexes
    op.drop_index(op.f('ix_sessions_last_seen'),
                  table_name='sessions')
    op.drop_table('sessions')
