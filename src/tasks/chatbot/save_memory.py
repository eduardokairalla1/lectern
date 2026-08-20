"""
Regenerates the conversation-memory summary.
"""

# --- IMPORTS ---
from src.clients.llms import MEMORY_LLM
from src.services.chatbot import memory as memory_service
from src.tasks.chatbot.config import RETRY_OPTIONS
from src.tasks.runner import run_async
from src.worker import celery_app


# --- CODE ---
@celery_app.task(name='chatbot.save_memory', **RETRY_OPTIONS)
def save_memory(
    session_id: str,
    user_message: str,
    assistant_response: str
) -> None:
    """
    Regenerates the conversation summary with the latest interaction.

    :param session_id: Conversation identifier.
    :param user_message: User's original message.
    :param assistant_response: Assistant response to persist.

    :returns: None.
    """
    run_async(
        memory_service.update_summary(
            llm=MEMORY_LLM,
            session_id=session_id,
            user_input=user_message,
            response=assistant_response,
        )
    )
