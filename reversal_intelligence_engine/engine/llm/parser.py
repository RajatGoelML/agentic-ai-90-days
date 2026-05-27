import json
def strip_markdown_fences(text: str) -> str:
    """Removes markdown code fences from LLM responses."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[1:end]).strip()
    return text
def parse_json_response(response: str, fallback: dict | None = None) -> dict:
    """
    Generic safe JSON parser for structured LLM outputs.
    No domain knowledge -- importable from any layer.
    Layer contract: tools/ -> core/llm OK, agents/ -> core/llm OK.
    """
    if fallback is None:
        fallback = {}
    try:
        clean = strip_markdown_fences(response)
        parsed = json.loads(clean)
        if isinstance(parsed, dict):
            return parsed
        return fallback
    except Exception as e:
        print(f"\n warning JSON parsing failed: {e}")
        return fallback
