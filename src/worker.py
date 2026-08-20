"""
Celery worker entrypoint.
"""

# --- IMPORTS ---
from celery import Celery
from src.config import config
from src.utils.logging_config import setup_logger


# --- GLOBALS ---
setup_logger()


# --- CODE ---
celery_app = Celery(
    'lectern_tasks',
    broker=config.REDIS_URL,
    backend=config.REDIS_URL,
    include=['src.tasks.chatbot'],
)

# basic Celery configuration
celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=300,
    task_soft_time_limit=240,
    task_ignore_result=True,
    broker_connection_retry_on_startup=True,

    # NOTE: without these, a broker that accepts the TCP connection but never
    #       answers (a half-open socket, an overloaded Redis, a stuck proxy)
    #       blocks the publisher forever: dispatch_task can swallow an
    #       exception, but it cannot swallow a hang, and the request that
    #       already produced its answer would never return. Publishing is
    #       fire-and-forget analytics, so it must fail fast and be logged.
    broker_transport_options={
        'socket_connect_timeout': 2,
        'socket_timeout': 2,
    },
    broker_connection_timeout=2,
    task_publish_retry_policy={'max_retries': 0},
)
