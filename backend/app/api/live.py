from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.live_social import live_social_service

router = APIRouter(prefix="/api/live", tags=["live"])


@router.get("/social")
def get_live_social() -> dict:
    return live_social_service.fetch_all(force=False)


@router.post("/social/refresh")
def refresh_live_social() -> dict:
    return live_social_service.fetch_all(force=True)


@router.post("/social/{source}/refresh")
def refresh_live_source(source: str) -> dict:
    if source not in live_social_service.supported_sources():
        raise HTTPException(status_code=400, detail="unsupported source")
    return live_social_service.fetch_source(source, force=True)
