"""Tiny local-LLM call through Ollama (stdlib only). Returns "" when the model is
unavailable, so a missing brain degrades the cell instead of crashing it."""

import json
import os
import sys
import time
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
if not OLLAMA_URL.startswith("http"):
    OLLAMA_URL = "http://" + OLLAMA_URL


def ask(prompt: str, model: str, system: str = None, max_tokens: int = 500,
        temperature: float = 0.4, timeout: float = 180) -> str:
    payload = {"model": model, "prompt": prompt, "stream": True, "keep_alive": "2m",
               "options": {"num_predict": max_tokens, "temperature": temperature}}
    if system:
        payload["system"] = system
    req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    deadline = time.monotonic() + timeout
    chunks = []
    try:
        # streamed, so giving up at the deadline (closing the socket) cancels generation
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for line in r:
                if not line.strip():
                    continue
                part = json.loads(line)
                if part.get("error"):
                    _warn(model, part["error"])
                    return ""
                chunks.append(part.get("response", ""))
                if part.get("done") or time.monotonic() > deadline:
                    break
    except Exception as e:
        _warn(model, e)
        return ""
    return "".join(chunks).strip()


def _warn(model, err):
    # degrade, but never silently: the caller sees an empty answer, the user sees why
    print(f"[triple-check] {model}: {err}", file=sys.stderr)
