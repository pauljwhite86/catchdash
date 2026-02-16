from __future__ import annotations

import httpx


def synthesize_with_kokoro(base_url: str, text: str, voice: str, timeout_seconds: float = 180.0) -> tuple[bytes, str]:
    payload = {
        'model': 'kokoro',
        'input': text,
        'voice': voice,
        'response_format': 'mp3',
    }
    fallback_payload = {
        'text': text,
        'voice': voice,
        'format': 'mp3',
    }
    with httpx.Client(timeout=timeout_seconds) as client:
        res = client.post(f"{base_url.rstrip('/')}/v1/audio/speech", json=payload)
        if res.status_code >= 400:
            res = client.post(f"{base_url.rstrip('/')}/synthesize", json=fallback_payload)
        res.raise_for_status()
        return res.content, res.headers.get('content-type', 'audio/mpeg')
