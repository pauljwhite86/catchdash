from __future__ import annotations

from pathlib import Path

import yaml

from app.domain.models import TopicConfig


def load_raw_config(path: str) -> dict:
    cfg_path = Path(path)
    if not cfg_path.exists():
        return {}
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}


def load_topics(path: str) -> list[TopicConfig]:
    data = load_raw_config(path)
    rows = data.get("topics", [])
    out: list[TopicConfig] = []
    for row in rows:
        try:
            out.append(TopicConfig.model_validate(row))
        except Exception:
            continue
    return out


def load_live_social_config(path: str) -> dict:
    data = load_raw_config(path)
    raw = data.get("live_social")
    if isinstance(raw, dict):
        return raw
    return {}
