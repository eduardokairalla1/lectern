"""
Execution type vocabulary.
"""
from typing import Literal
from typing import get_args


# --- CODE ---
ExecutionType = Literal[
    'chatbot_answer',
    'query_rewrite',
    'metadata_extraction',
]

# every known tag, in declaration order
EXECUTION_TYPES: tuple[str, ...] = get_args(ExecutionType)

# regex pattern to match any known tag or a custom execution ID
EXECUTION_TYPE_PATTERN = f'^({"|".join(EXECUTION_TYPES)}|execution_[0-9]+)$'
