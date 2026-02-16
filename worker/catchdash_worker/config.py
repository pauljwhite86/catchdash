from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    backend_base_url: str = "http://localhost:8080"
    kokoro_base_url: str = "http://localhost:8880"
    llm_provider: str = "ollama"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "qwen3:4b"

    # Backward-compatible aliases for existing deployments.
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    tts_voice: str = "af_heart"
    poll_seconds: int = 2
    worker_id: str = "worker-1"
    http_timeout_seconds: float = 20.0
    llm_timeout_seconds: float = 240.0
    tts_timeout_seconds: float = 240.0
    summary_char_limit: int = 2000
    summary_input_chars: int = 30000
    max_tts_chars: int = 14000

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CATCHDASH_WORKER_")


settings = WorkerSettings()
