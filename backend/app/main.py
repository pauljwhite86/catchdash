from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.live import router as live_router
from app.api.jobs import router as jobs_router
from app.api.topics import router as topics_router
from app.core.settings import settings

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "env": settings.app_env}


app.include_router(topics_router)
app.include_router(jobs_router)
app.include_router(live_router)
