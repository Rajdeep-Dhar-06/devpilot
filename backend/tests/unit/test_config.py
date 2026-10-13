from devpilot.core.config import Settings


def test_settings_default_values() -> None:
    settings = Settings(
        OPENAI_API_KEY="test-key",
        E2B_API_KEY="test-e2b",
        GITHUB_APP_ID=123,
        GITHUB_APP_PRIVATE_KEY_PATH="./dummy.pem",
        GITHUB_APP_INSTALLATION_ID=456,
    )
    assert settings.OPENAI_MODEL_PLANNER == "gpt-4o"
    assert settings.OPENAI_MODEL_IMPLEMENTER == "gpt-4o"
    assert settings.OPENAI_MODEL_REVIEWER == "gpt-4o-mini"
    assert settings.OPENAI_MODEL_QA == "gpt-4o-mini"
    assert settings.MAX_WORKERS_PARALLEL == 5
    assert settings.MAX_QA_REPAIR_ATTEMPTS == 3
    assert settings.WORKER_STEP_LIMIT == 20
    assert settings.WORKER_TIMEOUT_SECONDS == 300
    assert settings.LANGFUSE_PUBLIC_KEY == ""
    assert settings.LANGFUSE_SECRET_KEY == ""
    assert settings.LANGFUSE_HOST == "https://cloud.langfuse.com"
    assert settings.LOG_LEVEL == "INFO"


def test_settings_custom_values() -> None:
    settings = Settings(
        OPENAI_API_KEY="custom-key",
        E2B_API_KEY="custom-e2b",
        GITHUB_APP_ID=999,
        GITHUB_APP_PRIVATE_KEY_PATH="./key.pem",
        GITHUB_APP_INSTALLATION_ID=888,
        MAX_WORKERS_PARALLEL=3,
        MAX_QA_REPAIR_ATTEMPTS=2,
    )
    assert settings.MAX_WORKERS_PARALLEL == 3
    assert settings.MAX_QA_REPAIR_ATTEMPTS == 2
