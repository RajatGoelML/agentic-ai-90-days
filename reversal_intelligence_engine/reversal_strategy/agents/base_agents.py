# ================================
# Base Agent
# ================================

from reversal_strategy.agents.llm_client import call_llm


class BaseAgent:

    """
    Abstract base class for all reasoning agents.

    Provides a standardized execution lifecycle: build prompt,
    call the LLM, parse the response. Child agents implement
    build_prompt() and optionally override parse_response().
    """

    AGENT_NAME = "BASE_AGENT"

    # Override in child agents to inject a role-specific system prompt.
    SYSTEM_PROMPT: str = None

    # Override in child agents to control response token budget.
    MAX_TOKENS: int = 1200

    # Override in child agents to control output variability.
    TEMPERATURE: float = None  # None = use default from llm_config

    def build_prompt(self, *args, **kwargs):
        """Child agents must implement prompt construction."""
        raise NotImplementedError

    def parse_response(self, response):
        """Default pass-through parser. Override in child agents if needed."""
        return response

    def run(self, *args, **kwargs):
        """Executes the full agent reasoning cycle."""

        print(f"\nRunning agent: {self.AGENT_NAME}")

        prompt = self.build_prompt(*args, **kwargs)

        kwargs_llm = dict(
            caller=self.AGENT_NAME,
            system_prompt=self.SYSTEM_PROMPT,
            max_tokens=self.MAX_TOKENS,
        )
        if self.TEMPERATURE is not None:
            kwargs_llm["temperature"] = self.TEMPERATURE

        response = call_llm(prompt, **kwargs_llm)

        return self.parse_response(response)