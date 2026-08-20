"""
Task dispatching utility functions.
"""

# --- IMPORTS ---
from celery import Task
from typing import Any

import logging


# --- GLOBALS ---
logger = logging.getLogger(__name__)


# --- CODE ---
def dispatch_task(task: Task, **kwargs: Any) -> None:
    """
    Enqueues a Celery task, logging (never raising) on broker failure.

    :param task: The Celery task to enqueue.
    :param kwargs: Task keyword arguments (must be JSON-serializable).

    :returns: None.
    """
    # enqueue the task
    try:
        task.delay(**kwargs)

    # errors occurs: only log
    except Exception as e:
        logger.error('Failed to enqueue %s: %s', task.name, e)
