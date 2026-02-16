from __future__ import annotations

from app.core.settings import settings
from app.domain.models import TopicConfig
from app.topics.config_loader import load_topics


class TopicRegistry:
    def __init__(self) -> None:
        self._topics: dict[str, TopicConfig] = {}
        self.reload()

    def reload(self) -> None:
        topics = load_topics(settings.topics_config_path)
        self._topics = {row.topic_id: row for row in topics if row.enabled}

    def list_topics(self) -> list[TopicConfig]:
        return list(self._topics.values())

    def get_topic(self, topic_id: str) -> TopicConfig | None:
        return self._topics.get(topic_id)


topic_registry = TopicRegistry()
