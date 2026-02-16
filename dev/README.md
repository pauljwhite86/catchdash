# CatchDash Dev

Docker Compose orchestration for local CatchDash development.

## What this directory contains

- `compose.yaml`: service wiring for backend, frontend, and worker
- `.env.example`: frontend backend URL template (`VITE_BACKEND_BASE_URL`)

## Services

- `backend` (`:8080`): FastAPI API with configurable topic/facade pipeline
- `frontend` (`:5174`): Vite React app
- `worker`: persistent queue worker (Qwen3 summary + TTS)
- `kokoro` (`:8880`): TTS engine

## Prerequisites

- Docker Desktop
- `docker compose`
- Ollama running on host with Qwen3 model pulled
- Optional: `jq` for script output parsing

## Environment setup

```bash
cd catchdash/dev
cp .env.example .env
```

Edit `.env` and set:

```bash
VITE_BACKEND_BASE_URL=http://<YOUR-HOST-LAN-IP>:8080
CATCHDASH_WORKER_LLM_PROVIDER=ollama
CATCHDASH_WORKER_LLM_BASE_URL=
CATCHDASH_WORKER_LLM_API_KEY=
CATCHDASH_WORKER_LLM_MODEL=qwen3:4b
CATCHDASH_WORKER_OLLAMA_BASE_URL=http://host.docker.internal:11434
CATCHDASH_WORKER_OLLAMA_MODEL=qwen3:4b
```

Use your host machine LAN IP if you want to open frontend from another device (iPad/phone/laptop).

## Find your host LAN IP

macOS:
```bash
ipconfig getifaddr en0
```

Linux:
```bash
hostname -I
```

Windows (PowerShell):
```powershell
ipconfig
```

Then set `VITE_BACKEND_BASE_URL` in `.env`:

```bash
VITE_BACKEND_BASE_URL=http://192.168.x.x:8080
```

## Start core stack

```bash
cd catchdash/dev
docker compose up -d backend kokoro frontend worker
```

Check API:

```bash
curl -s http://localhost:8080/healthz | jq
```

## Start/stop worker

Start worker only:

```bash
cd catchdash/dev
docker compose up -d worker
```

Stop worker:

```bash
docker compose stop worker
```

## End-to-end smoke test

Basic smoke flow:

```bash
cd catchdash/dev
docker compose up -d backend frontend worker kokoro
curl -s http://localhost:8080/healthz | jq
curl -s http://localhost:8080/api/topics | jq
curl -s "http://localhost:8080/api/topics/news_live/items?force=true" | jq '.items | length'
```

Expected:

- backend is healthy
- topics are listed
- first topic refreshes and returns items
- TTS jobs can be queued from the frontend and processed by worker
