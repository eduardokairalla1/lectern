"""
Logging configuration for the application.
"""

# --- IMPORTS ---
from src.config import config

import colorlog
import logging


# --- CODE ---
def setup_logger() -> logging.Logger:
    """
    Set up the root logger.

    :return: Configured root logger.
    """
    # get log level from config, default to DEBUG if not a known level
    log_level = logging.getLevelNamesMapping().get(
        config.LOG_LEVEL.upper(), logging.DEBUG
    )

    # create color formatter
    formatter = colorlog.ColoredFormatter(
        '%(white)s%(asctime)s%(reset)s '
        '%(log_color)s%(levelname)-8s%(reset)s '
        '%(cyan)s[%(name)s]%(reset)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%',
    )

    # get root logger
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # remove existing handlers
    root_logger.handlers = []

    # add colored handler
    root_logger.addHandler(handler)

    # silence noisy external libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    # return the configured root logger
    return root_logger
