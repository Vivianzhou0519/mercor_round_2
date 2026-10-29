"""LLM calls via OpenRouter. The `anthropic` library is only the client: base_url points at OpenRouter and
it is paid with OPENROUTER_API_KEY. 'anthropic/claude-sonnet-5.5' is OpenRouter's name for the model.
LLM checks can only PASS / WARN / ERROR, never FAIL: an LLM's opinion flags, a human decides."""

from __future__ import annotations

import json
import os
import time

MODEL = "anthropic/claude-sonnet-5.5"


def ask_json(system: str, prompt: str, schema: dict) -> tuple[dict | None, dict]:
    """One structured-output call. Returns (parsed JSON or None, full record of the call for the evidence)."""
    rec = {"model": MODEL, "system": system, "prompt": prompt, "schema": schema}
    t0 = time.time()
    try:
        import anthropic
        client = anthropic.Anthropic(base_url="https://openrouter.ai/api", api_key=None,
                                     auth_token=os.environ["OPENROUTER_API_KEY"])
        resp = client.messages.create(
            model=MODEL, max_tokens=16000,
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
            system=system, messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in resp.content if b.type == "text")
        rec.update(raw_response=text, stop_reason=resp.stop_reason, seconds=round(time.time() - t0, 2),
                   usage=resp.usage.model_dump() if hasattr(resp.usage, "model_dump") else str(resp.usage))
        return json.loads(text), rec
    except Exception as e:  # any failure is ERROR for the check, recorded with the reason
        rec.update(error=f"{type(e).__name__}: {e}", seconds=round(time.time() - t0, 2))
        return None, rec
