"""
Shared chatbot pipeline.

Single source of truth for the ordered pre-answer steps
(load memory -> rewrite query -> retrieve context).

The answer step differs between paths (structured, one-shot answer vs. token
streaming), so it stays in each orchestrator; everything before it is shared.
"""

# --- IMPORTS ---

import time


# --- CODE ---
def elapsed_ms(start_time: float) -> int:
    """
    Elapsed time since the request started, in milliseconds.

    :param start_time: The timestamp when the request started.

    :return: Elapsed time in milliseconds.
    """
    return int((time.time() - start_time) * 1000)


