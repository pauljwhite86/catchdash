from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx

from app.domain.models import ContentItem, SourceConfig
from app.topics.facades.rss import RSSFacade


class ArxivFacade(RSSFacade):
    async def fetch_items(self, topic_id: str, source: SourceConfig, max_items: int) -> list[ContentItem]:
        items = await super().fetch_items(topic_id, source, max_items)
        if not items:
            items = await self._fetch_from_api(topic_id, source, max_items)
        for item in items:
            item.url = _to_arxiv_html_url(item.url)
            item.item_id = hashlib.sha256(
                f"{item.topic_id}|{item.source_id}|{item.url}".encode("utf-8")
            ).hexdigest()
            item.tts_modes = ["summary", "full_page"]
        return items

    async def _fetch_from_api(self, topic_id: str, source: SourceConfig, max_items: int) -> list[ContentItem]:
        category = source.metadata.get("category") if source.metadata else None
        if not category:
            category = _category_from_rss_url(source.url)
        if not category:
            category = "cs.CV"

        query_url = (
            "https://export.arxiv.org/api/query"
            f"?search_query=cat:{category}&start=0&max_results={max_items}"
            "&sortBy=submittedDate&sortOrder=descending"
        )

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            res = await client.get(query_url)
            res.raise_for_status()
            xml_text = res.text

        root = ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        out: list[ContentItem] = []
        for entry in root.findall("atom:entry", ns):
            title_node = entry.find("atom:title", ns)
            id_node = entry.find("atom:id", ns)
            summary_node = entry.find("atom:summary", ns)
            published_node = entry.find("atom:published", ns)
            if title_node is None or id_node is None:
                continue

            title = " ".join((title_node.text or "").split())
            link = _to_arxiv_html_url((id_node.text or "").strip())
            if not title or not link:
                continue
            key = hashlib.sha256(f"{topic_id}|{source.source_id}|{link}".encode("utf-8")).hexdigest()
            out.append(
                ContentItem(
                    item_id=key,
                    topic_id=topic_id,
                    source_id=source.source_id,
                    source_name=source.name,
                    title=title,
                    url=link,
                    published_at=_parse_iso_datetime(published_node.text if published_node is not None else None),
                    summary=((summary_node.text or "").strip() if summary_node is not None else "")[:1000],
                    image_url=None,
                )
            )
        return out


def _category_from_rss_url(url: str) -> str | None:
    marker = "/rss/"
    if marker not in url:
        return None
    category = url.split(marker, 1)[1].strip().strip("/")
    return category or None


def _to_arxiv_html_url(url: str) -> str:
    txt = (url or "").strip()
    if not txt:
        return txt
    if "/html/" in txt:
        return txt
    if "/abs/" in txt:
        return txt.replace("/abs/", "/html/")
    if "/pdf/" in txt:
        paper_id = txt.rsplit("/", 1)[-1].replace(".pdf", "")
        return f"https://arxiv.org/html/{paper_id}"
    return txt


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None
