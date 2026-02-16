from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Catchdash Backend"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8080
    topics_config_path: str = "config/topics.yaml"
    http_timeout_seconds: float = 12.0
    topic_cache_ttl_seconds: int = 30
    audio_dir: str = "/tmp/catchdash-audio"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CATCHDASH_")


settings = Settings()
