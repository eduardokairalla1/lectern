"""
LLM and embedding clients.
"""

# --- IMPORTS ---
from langchain_openai.embeddings import OpenAIEmbeddings
from src.config import config


# --- GLOBALS ---
EMBEDDING = OpenAIEmbeddings(
    openai_api_key=config.OPENAI_API_KEY_EMBEDDING,
    model=config.EMBEDDING_MODEL,
)
