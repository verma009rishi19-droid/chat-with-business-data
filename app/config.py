"""Application Configuration using Pydantic Settings."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google Gemini
    GOOGLE_API_KEY: str = Field(default="", description="Google GenAI API Key")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", description="Gemini model name")
    EMBEDDING_MODEL: str = Field(
        default="models/text-embedding-004", description="Gemini embedding model name"
    )

    # Database
    DB_TYPE: Literal["postgres", "sqlite"] = Field(
        default="postgres", description="Database dialect: postgres or sqlite"
    )
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgrespassword@localhost:5432/business_db",
        description="Admin Postgres connection string",
    )
    DATABASE_READONLY_URL: str = Field(
        default="postgresql://readonly_analyst:readonly_pass@localhost:5432/business_db",
        description="Read-only role Postgres connection string",
    )
    SQLITE_DB_PATH: str = Field(
        default=str(BASE_DIR / "data" / "warehouse.db"),
        description="Path to SQLite database file for local/fallback execution",
    )
    STATEMENT_TIMEOUT_MS: int = Field(
        default=5000, description="Max query execution timeout in milliseconds"
    )

    # Vector Store
    CHROMA_PERSIST_DIRECTORY: str = Field(
        default=str(BASE_DIR / "chroma_data"),
        description="Local storage path for Chroma vector database",
    )
    CHROMA_COLLECTION_NAME: str = Field(
        default="business_knowledge_base", description="Chroma collection name"
    )

    # Observability
    OBSERVABILITY_PROVIDER: Literal["langfuse", "langsmith", "none"] = Field(
        default="none", description="Observability platform"
    )
    LANGFUSE_PUBLIC_KEY: str = Field(default="", description="Langfuse Public Key")
    LANGFUSE_SECRET_KEY: str = Field(default="", description="Langfuse Secret Key")
    LANGFUSE_HOST: str = Field(default="https://cloud.langfuse.com", description="Langfuse Host")

    # API and UI
    API_PORT: int = Field(default=8000, description="FastAPI server port")
    UI_PORT: int = Field(default=8501, description="Streamlit UI server port")

    def get_database_url(self, readonly: bool = True) -> str:
        """Resolve database URL based on active DB_TYPE and required privilege."""
        if self.DB_TYPE == "sqlite":
            return f"sqlite:///{self.SQLITE_DB_PATH}"
        raw_url = self.DATABASE_READONLY_URL if readonly else self.DATABASE_URL
        if raw_url.startswith("postgresql://"):
            return raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return raw_url


settings = Settings()
