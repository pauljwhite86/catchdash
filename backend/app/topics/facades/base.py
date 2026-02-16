from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models import ContentItem, SourceConfig


class SourceFacade(ABC):
    @abstractmethod
    async def fetch_items(self, topic_id: str, source: SourceConfig, max_items: int) -> list[ContentItem]:
        raise NotImplementedError
