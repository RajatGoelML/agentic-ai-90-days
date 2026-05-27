# ================================
# LLM Client
# ================================

import os
import time
import threading

from dotenv import load_dotenv
from openai import OpenAI

try:
    import yaml as _yaml
    _CONFIG_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "infrastructure", "config", "llm_config.yaml"
    )
    with open(_CONFIG_PATH) as _f:
        _LLM_CONFIG = _yaml.safe_load(_f)
except Exception:
    _LLM_CONFIG = {}

_DEFAULT_MODEL       = _LLM_CONFIG.get("default_model",       "gpt-4.1-mini")
_DEFAULT_TEMPERATURE = _LLM_CONFIG.get("default_temperature", 0.2)
_DEFAULT_MAX_TOKENS  = _LLM_CONFIG.get("default_max_tokens",  1200)
_DEFAULT_RETRIES     = _LLM_CONFIG.get("retries",             2)
_RETRY_DELAY         = _LLM_CONFIG.get("retry_delay_seconds", 1)


# =========================================================
# Environment Initialization
# =========================================================

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY not found in environment"
    )


# =========================================================
# Shared OpenAI Client
# =========================================================

client = OpenAI(api_key=api_key)


# =========================================================
# Model Pricing (per 1M tokens, USD)
# Updated: May 2025. Adjust as pricing changes.
# =========================================================

MODEL_PRICING = {
    "gpt-4.1-mini": {
        "input": 0.40,
        "output": 1.60,
    },
    "gpt-4.1-nano": {
        "input": 0.10,
        "output": 0.40,
    },
    "gpt-4.1": {
        "input": 2.00,
        "output": 8.00,
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60,
    },
    "gpt-4o": {
        "input": 2.50,
        "output": 10.00,
    },
}

# Fallback pricing if model not in table
DEFAULT_PRICING = {"input": 1.00, "output": 3.00}


# =========================================================
# Token Usage Tracker (thread-safe)
# =========================================================

class TokenTracker:
    """
    Accumulates token usage across all LLM calls during a workflow run.
    Thread-safe for parallel node execution.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.calls = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0

    def record(self, model, input_tokens, output_tokens, caller=""):
        pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        call_cost = input_cost + output_cost

        with self._lock:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_cost_usd += call_cost
            self.calls.append({
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": round(call_cost, 6),
                "caller": caller,
            })

    def get_summary(self) -> dict:
        with self._lock:
            return {
                "total_llm_calls": len(self.calls),
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "total_tokens": self.total_input_tokens + self.total_output_tokens,
                "total_cost_usd": round(self.total_cost_usd, 6),
                "model_used": self.calls[0]["model"] if self.calls else "N/A",
                "calls_breakdown": self.calls,
            }

    def print_summary(self):
        s = self.get_summary()
        print(f"""
  LLM Token Usage
  ---------------
  Model           : {s['model_used']}
  Total LLM Calls : {s['total_llm_calls']}
  Input Tokens    : {s['total_input_tokens']:,}
  Output Tokens   : {s['total_output_tokens']:,}
  Total Tokens    : {s['total_tokens']:,}
  Estimated Cost  : ${s['total_cost_usd']:.4f} USD
""")

    def reset(self):
        with self._lock:
            self.calls.clear()
            self.total_input_tokens = 0
            self.total_output_tokens = 0
            self.total_cost_usd = 0.0


# Global tracker instance
token_tracker = TokenTracker()


# =========================================================
# Unified LLM Gateway
# =========================================================

DEFAULT_SYSTEM_PROMPT = (
    "You are a senior financial AI analyst.\n\n"
    "Always:\n"
    "- reason carefully\n"
    "- avoid hallucinations\n"
    "- remain concise\n"
    "- prioritize explainability\n"
    "- follow requested output structure strictly"
)


def call_llm(

    prompt: str,

    retries: int = _DEFAULT_RETRIES,

    model: str = _DEFAULT_MODEL,

    temperature: float = _DEFAULT_TEMPERATURE,

    max_tokens: int = _DEFAULT_MAX_TOKENS,

    caller: str = "",

    system_prompt: str = None,
) -> str:

    """
    Centralized gateway for all LLM interactions.

    Loads inference settings from config/llm_config.yaml (model,
    temperature, token budget, retry policy). Tracks token usage
    and cost via the global TokenTracker. Supports per-agent
    system prompt injection and configurable retry logic.
    """

    active_system_prompt = system_prompt if system_prompt else DEFAULT_SYSTEM_PROMPT

    # retries = number of extra attempts after the first failure
    max_attempts = retries + 1

    for attempt in range(max_attempts):

        try:

            response = client.chat.completions.create(

                model=model,

                temperature=temperature,

                max_tokens=max_tokens,

                messages=[

                    {
                        "role": "system",

                        "content": active_system_prompt
                    },

                    {
                        "role": "user",

                        "content": prompt
                    }
                ]
            )

            # -----------------------------------------
            # Track token usage
            # -----------------------------------------
            usage = response.usage
            if usage:
                token_tracker.record(
                    model=model,
                    input_tokens=usage.prompt_tokens,
                    output_tokens=usage.completion_tokens,
                    caller=caller,
                )

            content = (
                response
                .choices[0]
                .message
                .content
            )

            # -----------------------------------------
            # Guard against None responses
            # -----------------------------------------

            return content if content else ""

        except Exception as e:

            print(
                f"\n[LLM] Attempt "
                f"{attempt + 1}/{max_attempts} failed: {e}"
            )

            if attempt < max_attempts - 1:
                time.sleep(_RETRY_DELAY)

    # =====================================================
    # Hard failure after retries
    # =====================================================

    raise RuntimeError(
        "LLM failed after retries"
    )