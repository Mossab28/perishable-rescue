"""Thin OpenAI-compatible LLM client with cost tracking and a hard-fail-safe.

Every reasoning agent calls `chat()`. If no API key is configured or the call
fails, `chat()` raises LLMUnavailable and the agent uses its rule-based fallback.
The pipeline therefore NEVER crashes because of the model — it degrades.
"""
import json
import config

_total_cost = 0.0
_total_calls = 0


class LLMUnavailable(Exception):
    pass


def _client():
    from openai import OpenAI
    return OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)


def chat(system: str, user: str, max_tokens: int = 500, temperature: float = 0.4,
         force_json: bool = False) -> str:
    """Return the model's text. Raise LLMUnavailable on any problem."""
    global _total_cost, _total_calls
    if not config.LLM_ENABLED:
        raise LLMUnavailable("no API key configured")
    try:
        kwargs = dict(
            model=config.OPENAI_MODEL,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if force_json:
            kwargs["response_format"] = {"type": "json_object"}
        resp = _client().chat.completions.create(**kwargs)
        _total_calls += 1
        usage = getattr(resp, "usage", None)
        cost = getattr(usage, "cost", None) if usage else None
        if cost is not None:
            _total_cost += float(cost)
        return resp.choices[0].message.content or ""
    except LLMUnavailable:
        raise
    except Exception as e:  # network, auth, rate limit, bad model...
        raise LLMUnavailable(str(e))


def chat_json(system: str, user: str, max_tokens: int = 500, temperature: float = 0.4) -> dict:
    """Chat and parse a JSON object, tolerating code fences. Raise LLMUnavailable on failure."""
    raw = chat(system, user, max_tokens=max_tokens, temperature=temperature, force_json=True)
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1].lstrip("json").strip() if "```" in text[3:] else text.strip("`")
    try:
        return json.loads(text)
    except Exception as e:
        raise LLMUnavailable(f"bad JSON from model: {e}")


def stats() -> dict:
    return {"calls": _total_calls, "cost_usd": round(_total_cost, 6)}
