from __future__ import annotations

import json
from collections.abc import Callable

import httpx


def summarize_with_llm(
    *,
    provider: str,
    model: str,
    title: str,
    text: str,
    timeout_seconds: float = 240.0,
    max_input_chars: int = 30000,
    base_url: str | None = None,
    api_key: str | None = None,
    on_chunk: Callable[[dict], None] | None = None,
) -> str:
    prompt = (
        "You are summarizing an article for text-to-speech playback. "
        "Write a concise spoken-style summary in plain English, around 5 to 8 short paragraphs. "
        "Cover: what happened, why it matters, key details, and notable caveats. "
        "Do not use bullet points. Do not use markdown. Keep it factual.\n\n"
        f"Title: {title}\n\n"
        f"Article text:\n{text[:max_input_chars]}"
    )

    mode = (provider or "ollama").strip().lower()
    if mode == "ollama":
        return _summarize_with_ollama(
            base_url=base_url or "http://localhost:11434",
            model=model,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            on_chunk=on_chunk,
        )
    if mode in {"openai_compatible", "openai-compatible", "openai"}:
        return _summarize_with_openai_compatible(
            base_url=base_url or "https://api.openai.com/v1",
            api_key=api_key,
            model=model,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            on_chunk=on_chunk,
        )
    raise ValueError(f"unsupported llm provider: {provider}")


def _summarize_with_ollama(
    *,
    base_url: str,
    model: str,
    prompt: str,
    timeout_seconds: float,
    on_chunk: Callable[[dict], None] | None = None,
) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
    }

    parts: list[str] = []
    chunk_count = 0
    with httpx.Client(timeout=timeout_seconds) as client:
        with client.stream(
            "POST",
            f"{base_url.rstrip('/')}/api/generate",
            json=payload,
        ) as res:
            res.raise_for_status()
            for line in res.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                piece = data.get("response", "")
                if piece:
                    parts.append(piece)
                    chunk_count += 1
                    if on_chunk:
                        on_chunk({"chunk_count": chunk_count, "piece_chars": len(piece)})
                if data.get("done"):
                    break
    return "".join(parts).strip()


def _summarize_with_openai_compatible(
    *,
    base_url: str,
    api_key: str | None,
    model: str,
    prompt: str,
    timeout_seconds: float,
    on_chunk: Callable[[dict], None] | None = None,
) -> str:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise assistant for spoken summaries."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    with httpx.Client(timeout=timeout_seconds) as client:
        res = client.post(f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
        res.raise_for_status()
        data = res.json()
    content = (
        ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
        or ""
    ).strip()
    if on_chunk:
        on_chunk({"chunk_count": 1, "piece_chars": len(content)})
    return content
