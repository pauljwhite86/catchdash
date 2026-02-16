from __future__ import annotations

from app.domain.models import ContentItem, SourceConfig
from app.topics.facades.rss import RSSFacade


class MLBFacade(RSSFacade):
    async def fetch_items(self, topic_id: str, source: SourceConfig, max_items: int) -> list[ContentItem]:
        items = await super().fetch_items(topic_id, source, max_items)
        for item in items:
            item.tts_modes = ["full_page", "summary"]
        return items
