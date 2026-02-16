from __future__ import annotations

import asyncio
import html
import hashlib
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from app.domain.models import ContentItem, SourceConfig
from app.topics.facades.base import SourceFacade


class RSSFacade(SourceFacade):
    async def fetch_items(self, topic_id: str, source: SourceConfig, max_items: int) -> list[ContentItem]:
        # feedparser does blocking network I/O; run it in a worker thread.
        feed = await asyncio.to_thread(feedparser.parse, source.url)
        out: list[ContentItem] = []
        for entry in feed.entries[:max_items]:
            link = entry.get("link")
            title = _clean_text(entry.get("title") or "")
            if not link or not title:
                continue
            published = _parse_published(entry)
            image_url = _extract_image(entry)
            summary_raw = entry.get("summary") or entry.get("description") or ""
            key = hashlib.sha256(f"{topic_id}|{source.source_id}|{link}".encode("utf-8")).hexdigest()
            out.append(
                ContentItem(
                    item_id=key,
                    topic_id=topic_id,
                    source_id=source.source_id,
                    source_name=source.name,
                    title=title,
                    url=str(link),
                    published_at=published,
                    summary=_clean_text(summary_raw)[:1000],
                    image_url=image_url,
                )
            )
        return out


def _parse_published(entry: dict) -> datetime | None:
    for key in ("published", "updated"):
        val = entry.get(key)
        if not val:
            continue
        try:
            return parsedate_to_datetime(val)
        except Exception:
            continue
    return None


def _extract_image(entry: dict) -> str | None:
    media_content = entry.get("media_content")
    if isinstance(media_content, list) and media_content:
        first = media_content[0]
        if isinstance(first, dict) and first.get("url"):
            return str(first["url"])

    media_thumbnail = entry.get("media_thumbnail")
    if isinstance(media_thumbnail, list) and media_thumbnail:
        first = media_thumbnail[0]
        if isinstance(first, dict) and first.get("url"):
            return str(first["url"])

    image = entry.get("image")
    if isinstance(image, dict):
        maybe = image.get("href") or image.get("url")
        if maybe:
            return str(maybe)

    return None


def _clean_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
