"""OpenAI LLM client factory with tiered model strategy (Decision 10)."""

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from devpilot.core.config import settings


def get_llm_client(
    role: str = "implementer",
    model_name: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.2,
) -> ChatOpenAI:
    """Returns a ChatOpenAI instance configured according to the agent's role tier."""
    if not model_name:
        match role:
            case "planner":
                model_name = settings.OPENAI_MODEL_PLANNER
            case "implementer":
                model_name = settings.OPENAI_MODEL_IMPLEMENTER
            case "reviewer":
                model_name = settings.OPENAI_MODEL_REVIEWER
            case "qa":
                model_name = settings.OPENAI_MODEL_QA
            case "worker":
                model_name = settings.OPENAI_MODEL_REVIEWER
            case _:
                model_name = settings.OPENAI_MODEL_IMPLEMENTER

    resolved_api_key = api_key or settings.OPENAI_API_KEY or "dummy_key"

    return ChatOpenAI(
        model=model_name,
        api_key=SecretStr(resolved_api_key),
        temperature=temperature,
    )
