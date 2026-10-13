from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """DevPilot global application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Settings (OpenAI Tiered Models - Decision 10)
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    OPENAI_MODEL_PLANNER: str = Field(
        default="gpt-4o",
        description="Model for Planner agent",
    )
    OPENAI_MODEL_IMPLEMENTER: str = Field(
        default="gpt-4o",
        description="Model for Implementer agent",
    )
    OPENAI_MODEL_REVIEWER: str = Field(
        default="gpt-4o-mini",
        description="Model for Reviewer agents",
    )
    OPENAI_MODEL_QA: str = Field(
        default="gpt-4o-mini",
        description="Model for QA evaluation",
    )

    # E2B Sandbox
    E2B_API_KEY: str = Field(default="", description="E2B API key")

    # GitHub App (Decision 11)
    GITHUB_APP_ID: int = Field(default=0, description="GitHub App ID")
    GITHUB_APP_PRIVATE_KEY_PATH: str = Field(
        default="",
        description="Path to GitHub App private key PEM file",
    )
    GITHUB_APP_INSTALLATION_ID: int = Field(default=0, description="GitHub App installation ID")

    # Database & Checkpointing (Decisions 5 & 9)
    DATABASE_URL: str = Field(
        default="postgresql://devpilot:devpilot_secret@localhost:5432/devpilot",
        description="PostgreSQL connection string with pgvector support",
    )

    # Worker & Execution Limits (Decisions 12, 18, 19)
    MAX_WORKERS_PARALLEL: int = Field(
        default=5,
        description="Max concurrent subagents for Implementer",
    )
    MAX_QA_REPAIR_ATTEMPTS: int = Field(default=3, description="Max QA fix repair cycles")
    WORKER_STEP_LIMIT: int = Field(default=20, description="Max tool steps per delegated worker")
    WORKER_TIMEOUT_SECONDS: int = Field(
        default=300,
        description="Max execution duration in seconds per worker",
    )

    # Observability (Langfuse)
    LANGFUSE_PUBLIC_KEY: str = Field(default="", description="Langfuse public key")
    LANGFUSE_SECRET_KEY: str = Field(default="", description="Langfuse secret key")
    LANGFUSE_HOST: str = Field(
        default="https://cloud.langfuse.com",
        description="Langfuse host URL",
    )

    # Logging & Diagnostics (Pydantic Logfire)
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    LOGFIRE_TOKEN: str = Field(default="", description="Logfire write token")
    LOGFIRE_SEND_TO_LOGFIRE: bool = Field(
        default=False,
        description="Whether to export spans and logs to Logfire cloud",
    )


settings = Settings()
