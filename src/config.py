"""
Application configuration.
"""

# --- IMPORTS ---
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from typing import ClassVar


# --- CONFIG ---
class Config(BaseSettings):
    """
    Reads configuration from environment variables and .env file.
    """

    # general
    ENVIRONMENT: str = 'development'
    LOG_LEVEL: str = 'DEBUG'

    # the subject this instance speaks for
    IDENTITY_FILE: str = 'identity.yaml'

    # api keys
    OPENAI_API_KEY_PRINCIPAL: str
    OPENAI_API_KEY_MEMORY: str
    OPENAI_API_KEY_EMBEDDING: str
    OPENAI_API_KEY_TRANSCRIBE: str
    OPENAI_API_KEY_REWRITE: str

    # ai models
    PRINCIPAL_MODEL: str
    MEMORY_MODEL: str
    REWRITE_MODEL: str
    TRANSCRIBE_MODEL: str
    EMBEDDING_MODEL: str

    # databases
    QDRANT_URL: str
    VECTOR_COLLECTION: str = 'lectern_documents'
    REDIS_URL: str
    DATABASE_URL: str

    # routing
    API_PREFIX: str = '/api'

    # security
    API_KEY: str

    # audio limits
    MAX_AUDIO_DURATION_SECONDS: int = 120
    MAX_AUDIO_BASE64_SIZE: int = 10 * 1024 * 1024

    # audio formats
    AUDIO_SUPPORTED_FORMATS: ClassVar[list[str]] = [
        'mp3',
        'mp4',
        'mpeg',
        'mpga',
        'm4a',
        'wav',
        'webm',
        'ogg',
    ]

    # cors
    CORS_ORIGINS: str = 'http://localhost:*'

    @property
    def cors_origins(self) -> list[str]:
        """
        Parses CORS_ORIGINS into a list.

        :return: List of allowed CORS origins.
        """
        return [o.strip() for o in self.CORS_ORIGINS.split(',') if o.strip()]

    # pydantic settings
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


# shared singleton: import `config` instead of instantiating Config again
config = Config()
