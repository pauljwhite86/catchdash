# CatchDash Worker

Async worker for CatchDash.

## Role

- Poll/consume jobs from backend queue API
- Execute long-running tasks (TTS full page, TTS summary)
- Report progress/state via backend contract

Worker stays stateless by design. Queue persistence can evolve (SQL now, Redis later) without changing worker process model.

## Run local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m catchdash_worker.main
```

## Env

- `CATCHDASH_WORKER_BACKEND_BASE_URL=http://localhost:8080`
- `CATCHDASH_WORKER_LLM_PROVIDER=ollama` (`ollama` or `openai_compatible`)
- `CATCHDASH_WORKER_LLM_MODEL=qwen3:4b` (or any provider model id)
- `CATCHDASH_WORKER_LLM_BASE_URL=` (optional override)
- `CATCHDASH_WORKER_LLM_API_KEY=` (for API-key providers)
- `CATCHDASH_WORKER_OLLAMA_BASE_URL=http://localhost:11434` (used by `ollama`)
- `CATCHDASH_WORKER_OLLAMA_MODEL=qwen3:4b` (backward-compatible alias)
- `CATCHDASH_WORKER_KOKORO_BASE_URL=http://localhost:8880`
- `CATCHDASH_WORKER_POLL_SECONDS=2`
- `CATCHDASH_WORKER_WORKER_ID=worker-1`

## Cloud notes

- Deploy as long-running service/container (Fly, Render, Railway, ECS, K8s).
- Horizontal scale by adding replicas once queue claim semantics are in place.
