# CatchDash Backend

FastAPI backend for CatchDash.

## Architecture

- `app/topics/topic_live.py`: reusable configurable topic pipeline
- `app/topics/facades/`: modular source adapters (rss, arxiv, mlb)
- `config/topics.yaml`: all topics/sources are config-driven
- `app/api/topics.py`: sync fetch endpoints
- `app/api/jobs.py`: queue API contract (currently in-memory stub)

## Run local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8080
```

## Run Docker

```bash
docker build -t catchdash-backend .
docker run --rm -p 8080:8080 catchdash-backend
```

## API

- `GET /api/topics`
- `GET /api/topics/{topic_id}/items?force=true`
- `POST /api/jobs`
- `GET /api/jobs`

## Config

Set env vars with `CATCHDASH_` prefix, e.g.:

- `CATCHDASH_TOPICS_CONFIG_PATH=config/topics.yaml`
- `CATCHDASH_TOPIC_CACHE_TTL_SECONDS=30`

## Cloud deployment notes

- Stateless API container: works on Fly/Render/Railway/ECS/Cloud Run.
- Swap in Redis queue by replacing jobs API internals with queue adapter while keeping contract stable.
