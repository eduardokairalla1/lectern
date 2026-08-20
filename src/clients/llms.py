"""
LLM and embedding clients.
"""

# --- IMPORTS ---
from langchain_openai.embeddings import OpenAIEmbeddings
from openai import AsyncOpenAI
from src.config import config


# --- GLOBALS ---
TRANSCRIBE_LLM = AsyncOpenAI(api_key=config.OPENAI_API_KEY_TRANSCRIBE)

EMBEDDING = OpenAIEmbeddings(
    openai_api_key=config.OPENAI_API_KEY_EMBEDDING,
    model=config.EMBEDDING_MODEL,
)
