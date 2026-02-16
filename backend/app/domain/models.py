from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


FetchMode = Literal["full_page", "summary"]


class SourceConfig(BaseModel):
    source_id: str
    name: str
    adapter: str
    url: str
    enabled: bool = True
    metadata: dict[str, str] = Field(default_factory=dict)


class TopicConfig(BaseModel):
    topic_id: str
    name: str
    icon: str | None = None
    enabled: bool = True
    default_tts_mode: FetchMode = "full_page"
    max_items: int = 40
    sources: list[SourceConfig] = Field(default_factory=list)


class ContentItem(BaseModel):
    item_id: str
    topic_id: str
    source_id: str
    source_name: str
    title: str
    url: str
    published_at: datetime | None = None
    summary: str | None = None
    image_url: str | None = None
    tts_modes: list[FetchMode] = Field(default_factory=lambda: ["full_page", "summary"])


class TopicItemsResponse(BaseModel):
    topic_id: str
    topic_name: str
    updated_at: datetime
    items: list[ContentItem]
