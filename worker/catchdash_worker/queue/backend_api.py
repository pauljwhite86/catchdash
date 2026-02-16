from __future__ import annotations

from typing import Any

import httpx


class BackendQueueAPI:
    def __init__(self, base_url: str, timeout_seconds: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def list_jobs(self) -> list[dict[str, Any]]:
        with httpx.Client(timeout=self.timeout_seconds) as client:
            res = client.get(self._url("/api/jobs"))
            res.raise_for_status()
            return res.json().get("jobs", [])

    def get_job(self, job_id: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout_seconds) as client:
            res = client.get(self._url(f"/api/jobs/{job_id}"))
            res.raise_for_status()
            return res.json()

    def update_job(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout_seconds) as client:
            res = client.put(self._url(f"/api/jobs/{job_id}"), json=payload)
            res.raise_for_status()
            return res.json()

    def get_topic_item(self, topic_id: str, item_id: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout_seconds) as client:
            res = client.get(self._url(f"/api/topics/{topic_id}/items/{item_id}"))
            res.raise_for_status()
            return res.json()

    def upload_job_audio(self, job_id: str, audio_bytes: bytes, mime_type: str = "audio/mpeg") -> dict[str, Any]:
        files = {"file": (f"{job_id}.mp3", audio_bytes, mime_type)}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            res = client.post(self._url(f"/api/jobs/{job_id}/audio"), files=files)
            res.raise_for_status()
            return res.json()
