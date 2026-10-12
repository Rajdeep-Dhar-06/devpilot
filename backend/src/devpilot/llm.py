"""OpenAI language model client factory with role tiering.

Beginner Guide:
Different tasks have different intelligence vs. cost trade-offs:
- Complex planning and coding use stronger reasoning models (e.g. gpt-4o).
- Reviewing, testing, and subagent workers use fast, cost-efficient models (e.g. gpt-4o-mini).
"""

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from devpilot.core.config import settings


def get_llm(
    role: str = "implementer",
    model_name: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.2,
) -> ChatOpenAI:
    """Returns a configured ChatOpenAI instance based on the agent's role tier."""
    if not model_name:
        role_to_model = {
            "planner": settings.OPENAI_MODEL_PLANNER,
            "implementer": settings.OPENAI_MODEL_IMPLEMENTER,
            "reviewer": settings.OPENAI_MODEL_REVIEWER,
            "qa": settings.OPENAI_MODEL_QA,
            "worker": settings.OPENAI_MODEL_REVIEWER,
        }
        model_name = role_to_model.get(role, settings.OPENAI_MODEL_IMPLEMENTER)

    resolved_key = api_key or settings.OPENAI_API_KEY or "dummy-key"

    return ChatOpenAI(
        model=model_name,
        api_key=SecretStr(resolved_key),
        temperature=temperature,
    )
