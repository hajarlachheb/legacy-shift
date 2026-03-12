from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    azure_api_key: str = ""
    azure_api_base: str = ""
    default_model: str = "gpt-4o"

    # Azure OpenAI
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment_id: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"

    # Free local model (Ollama) — no API key, runs on your machine
    ollama_base_url: str = "http://localhost:11434"

    # Postgres / pgvector
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "legacy_shift"
    postgres_user: str = "legacy_shift"
    postgres_password: str = "changeme"

    # Observability
    langsmith_api_key: str = ""
    langsmith_project: str = "legacy-shift"
    phoenix_endpoint: str = "http://localhost:6006"

    # General
    log_level: str = "INFO"
    max_retries: int = 3

    # API limits and timeouts
    max_source_code_chars: int = 200_000
    migration_timeout_seconds: int = 600

    # CORS (comma-separated origins, or "*" for allow all)
    cors_origins: str = "*"

    # Rate limit: requests per minute per IP for /migrate and /explain (0 = disabled)
    rate_limit_per_minute: int = 0

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def get_settings() -> Settings:
    return Settings()
