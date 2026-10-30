import os
import time
import json
import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


def get_models():
    resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
    resp.raise_for_status()
    return resp.json().get("models", [])


def pull_model(model_name):
    # streams progress back as newline-delimited JSON
    with requests.post(
        f"{OLLAMA_HOST}/api/pull",
        json={"name": model_name},
        stream=True,
        timeout=600,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                yield json.loads(line)


def run_prompt(model, prompt):
    start = time.time()
    first_token_ms = None
    full_response = []
    total_tokens = 0

    with requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={"model": model, "prompt": prompt, "stream": True},
        stream=True,
        timeout=120,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)

            if first_token_ms is None and chunk.get("response"):
                first_token_ms = (time.time() - start) * 1000

            if chunk.get("response"):
                full_response.append(chunk["response"])

            if chunk.get("done"):
                eval_count = chunk.get("eval_count", 0)
                eval_duration = chunk.get("eval_duration", 1)
                total_tokens = eval_count
                tokens_per_sec = eval_count / (eval_duration / 1e9) if eval_duration else 0
                break

    total_ms = (time.time() - start) * 1000

    return {
        "response": "".join(full_response),
        "tokens_per_sec": round(tokens_per_sec, 2),
        "first_token_ms": round(first_token_ms or 0, 2),
        "total_ms": round(total_ms, 2),
        "total_tokens": total_tokens,
    }
