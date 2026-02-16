from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.topics.registry import topic_registry
from app.topics.topic_live import TopicLiveService

router = APIRouter(prefix="/api/topics", tags=["topics"])
service = TopicLiveService()


@router.get("")
def list_topics() -> dict:
    rows = topic_registry.list_topics()
    return {
        "topics": [
            {
                "topic_id": row.topic_id,
                "name": row.name,
                "icon": row.icon,
                "default_tts_mode": row.default_tts_mode,
                "sources": [
                    {
                        "source_id": src.source_id,
                        "name": src.name,
                        "adapter": src.adapter,
                        "url": src.url,
                    }
                    for src in row.sources
                    if src.enabled
                ],
            }
            for row in rows
        ]
    }


@router.get("/{topic_id}/items")
async def get_topic_items(topic_id: str, force: bool = False) -> dict:
    topic = topic_registry.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="topic not found")
    payload = await service.fetch_topic(topic, force=force)
    return payload.model_dump(mode="json")


@router.get("/{topic_id}/items/{item_id}")
async def get_topic_item(topic_id: str, item_id: str) -> dict:
    topic = topic_registry.get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="topic not found")
    payload = await service.fetch_topic(topic, force=False)
    item = next((row for row in payload.items if row.item_id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="item not found")
    return item.model_dump(mode="json")
