# CatchDash Frontend

Frontend for CatchDash.

## Principles

- Backend URL via env (`VITE_BACKEND_BASE_URL`)
- Topic-driven UI (no hard-coded widget business logic)
- TTS actions use backend job API

## Run local

```bash
npm install
npm run dev
```

Set API base URL:

```bash
export VITE_BACKEND_BASE_URL=http://localhost:8080
```

## Build

```bash
npm run build
```
