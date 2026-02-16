from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from app.domain.models import ContentItem, TopicConfig, TopicItemsResponse
from app.topics.facades import FACADE_REGISTRY


class TopicLiveService:
    def __init__(self, cache_ttl_seconds: int = 30, source_timeout_seconds: float = 20.0) -> None:
        self._cache: dict[str, tuple[datetime, TopicItemsResponse]] = {}
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._source_timeout_seconds = source_timeout_seconds

    async def fetch_topic(self, topic: TopicConfig, force: bool = False) -> TopicItemsResponse:
        now = datetime.now(timezone.utc)
        cached = self._cache.get(topic.topic_id)
        if not force and cached and now - cached[0] <= self._cache_ttl:
            return cached[1]

        tasks: list[asyncio.Task[list[ContentItem]]] = []
        for source in topic.sources:
            if not source.enabled:
                continue
            facade_type = FACADE_REGISTRY.get(source.adapter)
            if not facade_type:
                continue
            facade = facade_type()
            tasks.append(asyncio.create_task(self._fetch_source(facade, topic.topic_id, source, topic.max_items)))

        rows: list[ContentItem] = []
        if tasks:
            for task in asyncio.as_completed(tasks):
                try:
                    rows.extend(await task)
                except Exception:
                    continue

        deduped = _dedupe_items(rows)
        deduped.sort(key=lambda x: _sort_key(x.published_at), reverse=True)

        payload = TopicItemsResponse(
            topic_id=topic.topic_id,
            topic_name=topic.name,
            updated_at=now,
            items=deduped[: topic.max_items],
        )
        self._cache[topic.topic_id] = (now, payload)
        return payload

    async def _fetch_source(self, facade, topic_id: str, source, max_items: int) -> list[ContentItem]:
        async with asyncio.timeout(self._source_timeout_seconds):
            return await facade.fetch_items(topic_id, source, max_items)


def _dedupe_items(items: list[ContentItem]) -> list[ContentItem]:
    seen: set[str] = set()
    out: list[ContentItem] = []
    for item in items:
        key = f"{item.source_id}:{item.url}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _sort_key(value: datetime | None) -> float:
    if value is None:
        return 0.0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()
