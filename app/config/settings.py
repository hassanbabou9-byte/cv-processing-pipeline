"""
Application settings.

Single source of truth for all configuration. Values are read from
environment variables / a .env file and validated once at startup.

No other module should call os.getenv() directly — everything goes
through `get_settings()`.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized, validated application configuration.

    Every field maps to an environment variable of the same name
    (case-insensitive).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------
    # App metadata
    # ------------------------------------------------------------

    app_name: str = "CV Processing Pipeline"
    app_version: str = "0.1.0"

    environment: Literal[
        "development",
        "staging",
        "production",
    ] = "development"

    # ------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------

    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    # ------------------------------------------------------------
    # LLM provider selection
    # ------------------------------------------------------------

    llm_provider: Literal[
        "openrouter",
        "ollama",
    ] = "ollama"

    # ------------------------------------------------------------
    # LLM behavior
    # ------------------------------------------------------------

    llm_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
    )

    llm_max_retries: int = Field(
        default=2,
        ge=0,
    )

    llm_timeout_seconds: int = Field(
        default=60,
        ge=1,
    )

    llm_parse_retries: int = Field(
        default=2,
        ge=0,
    )

    llm_max_output_tokens: int = Field(
        default=4096,
        ge=256,
    )

    llm_context_window: int = Field(
        default=8192,
        ge=1024,
    )

    # ------------------------------------------------------------
    # OpenRouter provider config
    # ------------------------------------------------------------

    openrouter_api_key: str | None = None

    openrouter_base_url: str = (
        "https://openrouter.ai/api/v1"
    )

    openrouter_model: str = (
        "openai/gpt-4o-mini"
    )

    # ------------------------------------------------------------
    # Ollama provider config
    # ------------------------------------------------------------

    ollama_base_url: str = (
        "http://localhost:11434"
    )

    ollama_model: str = "llama3.1"

    # ------------------------------------------------------------
    # Database
    # ------------------------------------------------------------

    database_url: str = (
        "postgresql+psycopg://postgres:postgres"
        "@localhost:5432/cv_pipeline"
    )

    # ------------------------------------------------------------
    # MinIO Object Storage
    # ------------------------------------------------------------

    minio_endpoint: str = "minio:9000"

    minio_access_key: str = "minioadmin"

    minio_secret_key: str = "minioadmin"

    minio_bucket: str = "candidate-images"

    minio_secure: bool = False

    # ------------------------------------------------------------
    # File upload constraints
    # ------------------------------------------------------------

    max_upload_size_mb: int = Field(
        default=10,
        ge=1,
    )

    allowed_upload_extensions: tuple[str, ...] = (
        ".pdf",
        ".docx",
    )

    # ------------------------------------------------------------
    # Local storage
    # ------------------------------------------------------------

    upload_storage_dir: str = (
        "data/uploads"
    )

    parsed_storage_dir: str = (
        "data/parsed"
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    The .env file / environment is read and validated once
    per process.
    """

    return Settings()