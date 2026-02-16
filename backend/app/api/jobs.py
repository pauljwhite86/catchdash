from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.settings import settings

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    type: Literal["tts_full_page", "tts_summary"]
    topic_id: str
    item_id: str


class JobStatus(BaseModel):
    id: str
    type: str
    topic_id: str
    item_id: str
    status: str
    progress: int
    message: str | None = None
    output_ref: str | None = None
    created_at: datetime
    updated_at: datetime


class UpdateJobRequest(BaseModel):
    status: str | None = None
    progress: int | None = None
    message: str | None = None
    output_ref: str | None = None


# Placeholder in-memory store so queue backend can be swapped later.
JOBS: dict[str, JobStatus] = {}


@router.post("")
def create_job(payload: CreateJobRequest) -> dict:
    job_id = str(uuid4())
    row = JobStatus(
        id=job_id,
        type=payload.type,
        topic_id=payload.topic_id,
        item_id=payload.item_id,
        status="queued",
        progress=0,
        message="queued",
        output_ref=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    JOBS[job_id] = row
    return row.model_dump(mode="json")


@router.get("")
def list_jobs() -> dict:
    return {"jobs": [row.model_dump(mode="json") for row in JOBS.values()]}


@router.get("/{job_id}")
def get_job(job_id: str) -> dict:
    row = JOBS.get(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    return row.model_dump(mode="json")


@router.put("/{job_id}")
def update_job(job_id: str, payload: UpdateJobRequest) -> dict:
    row = JOBS.get(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    if payload.status is not None:
        row.status = payload.status
    if payload.progress is not None:
        row.progress = max(0, min(100, payload.progress))
    if payload.message is not None:
        row.message = payload.message
    if payload.output_ref is not None:
        row.output_ref = payload.output_ref
    row.updated_at = datetime.now(timezone.utc)
    JOBS[job_id] = row
    return row.model_dump(mode="json")


@router.post("/{job_id}/audio")
async def upload_job_audio(job_id: str, file: UploadFile = File(...)) -> dict:
    row = JOBS.get(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    payload = await file.read()
    audio_dir = Path(settings.audio_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)
    target = audio_dir / f"{job_id}.mp3"
    target.write_bytes(payload)
    row.output_ref = f"/api/jobs/audio/{target.name}"
    row.updated_at = datetime.now(timezone.utc)
    JOBS[job_id] = row
    return {"job_id": job_id, "output_ref": row.output_ref}


@router.get("/audio/{filename}")
def get_audio(filename: str):
    target = Path(settings.audio_dir) / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="audio not found")
    return FileResponse(target, media_type="audio/mpeg")
