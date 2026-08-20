"""
LLM and embedding clients.
"""

# --- IMPORTS ---
from langchain_openai.chat_models import ChatOpenAI
from langchain_openai.embeddings import OpenAIEmbeddings
from openai import AsyncOpenAI
from src.config import config
from src.schemas.outputparser import ResponseOutputParser


# --- GLOBALS ---
ASSISTANT_LLM = ChatOpenAI(
    api_key=config.OPENAI_API_KEY_PRINCIPAL,
    model=config.PRINCIPAL_MODEL,
    max_tokens=500,
)

STRUCTURED_ASSISTANT_LLM = ASSISTANT_LLM.with_structured_output(
    ResponseOutputParser, include_raw=True
)

MEMORY_LLM = ChatOpenAI(
    api_key=config.OPENAI_API_KEY_MEMORY, model=config.MEMORY_MODEL
)

REWRITE_MODEL = ChatOpenAI(
    api_key=config.OPENAI_API_KEY_REWRITE, model=config.REWRITE_MODEL
)

TRANSCRIBE_LLM = AsyncOpenAI(api_key=config.OPENAI_API_KEY_TRANSCRIBE)

EMBEDDING = OpenAIEmbeddings(
    openai_api_key=config.OPENAI_API_KEY_EMBEDDING,
    model=config.EMBEDDING_MODEL,
)
