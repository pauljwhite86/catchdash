from __future__ import annotations

import datetime as dt
import html
import logging
import re
import threading
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.settings import settings
from app.topics.config_loader import load_live_social_config

logger = logging.getLogger(__name__)


@dataclass
class LiveItem:
    source: str
    topic: str
    timestamp: dt.datetime
    raw_id: str
    title: str
    text: str
    author: str
    url: str
    media_urls: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": f"{self.source}:{self.raw_id}",
            "source": self.source,
            "topic": self.topic,
            "timestamp": self.timestamp.isoformat(),
            "title": self.title,
            "text": self.text,
            "author": self.author,
            "url": self.url,
            "media": [{"type": "image", "url": u} for u in self.media_urls],
        }


class LiveSocialService:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()
        self._ttl_seconds = 15.0

    def supported_sources(self) -> set[str]:
        return {str(src.get("source_id") or "") for src in self._sources_cfg() if src.get("enabled", True)}

    def fetch_all(self, force: bool = False) -> dict[str, Any]:
        now = dt.datetime.now(dt.UTC)
        refresh_interval = int(self._live_cfg().get("refresh_interval_seconds", 30))
        max_all = int(self._live_cfg().get("interleaved_limit", 24))
        source_rows = []
        merged_items: list[dict[str, Any]] = []

        for src in self._sources_cfg():
            if not src.get("enabled", True):
                continue
            source_id = str(src.get("source_id") or "")
            payload = self.fetch_source(source_id, force=force)
            source_rows.append(payload)
            merged_items.extend(payload.get("items", []))

        merged_items.sort(key=lambda x: _sort_key(x.get("timestamp")), reverse=True)
        return {
            "updated_at": now.isoformat(),
            "refresh_interval_seconds": refresh_interval,
            "items": merged_items[:max_all],
            "sources": source_rows,
        }

    def fetch_source(self, source: str, force: bool = False) -> dict[str, Any]:
        source_cfg = self._source_cfg(source)
        if not source_cfg or not source_cfg.get("enabled", True):
            raise ValueError(f"unsupported source: {source}")

        now = dt.datetime.now(dt.UTC)
        now_ts = now.timestamp()
        cache_key = f"source:{source}"

        with self._lock:
            cached = self._cache.get(cache_key)
            if not force and cached and now_ts - cached[0] <= self._ttl_seconds:
                return cached[1]

        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                items = self._fetch_source_items(client, source_cfg)
            error = None
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("live source fetch failed source=%s err=%s", source, exc)
            items = []
            error = str(exc)

        deduped: dict[str, LiveItem] = {}
        for item in items:
            deduped[f"{item.source}:{item.raw_id}"] = item
        merged = sorted(deduped.values(), key=lambda x: x.timestamp, reverse=True)[: int(source_cfg.get("max_items", 6))]

        payload = {
            "source_id": source,
            "name": str(source_cfg.get("name") or source.title()),
            "icon": str(source_cfg.get("icon") or "•"),
            "updated_at": now.isoformat(),
            "items": [row.as_dict() for row in merged],
            "error": error,
        }
        with self._lock:
            self._cache[cache_key] = (now_ts, payload)
        return payload

    def _fetch_source_items(self, client: httpx.Client, source_cfg: dict[str, Any]) -> list[LiveItem]:
        source_type = str(source_cfg.get("type") or "").lower()
        if source_type == "mastodon":
            return self._fetch_mastodon(client, source_cfg)
        if source_type == "reddit":
            return self._fetch_reddit(client, source_cfg)
        if source_type == "hackernews":
            return self._fetch_hackernews(client, source_cfg)
        if source_type == "bluesky_api":
            return self._fetch_bluesky_api(client, source_cfg)
        if source_type == "bluesky_links":
            return self._fetch_bluesky_links(source_cfg)
        return []

    def _fetch_mastodon(self, client: httpx.Client, source_cfg: dict[str, Any]) -> list[LiveItem]:
        out: list[LiveItem] = []
        base_url = str(source_cfg.get("instance_base_url", "https://mastodon.social")).rstrip("/")
        tags = [str(tag).strip().lstrip("#") for tag in source_cfg.get("tags", []) if str(tag).strip()]
        topic = str(source_cfg.get("topic", "ai"))
        limit_per_tag = int(source_cfg.get("limit_per_tag", 8))
        max_tags = int(source_cfg.get("max_tags", 3))

        for hashtag in tags[:max_tags]:
            res = client.get(f"{base_url}/api/v1/timelines/tag/{hashtag}", params={"limit": limit_per_tag})
            res.raise_for_status()
            for row in res.json():
                content_text = _strip_html(row.get("content", ""))
                language = str(row.get("language") or "").lower()
                if language and language != "en":
                    continue
                if not language and not _looks_english(content_text):
                    continue
                created_at = _parse_datetime(row.get("created_at"))
                if not created_at:
                    continue
                account = row.get("account") or {}
                media = [a.get("preview_url") for a in row.get("media_attachments", []) if a.get("preview_url")]
                out.append(
                    LiveItem(
                        source=str(source_cfg.get("source_id") or "mastodon"),
                        topic=topic,
                        timestamp=created_at,
                        raw_id=str(row.get("id") or row.get("uri") or row.get("url") or ""),
                        title=_trim(content_text, 120) or "Mastodon post",
                        text=_trim(content_text, 320),
                        author=str(account.get("display_name") or account.get("acct") or ""),
                        url=str(row.get("url") or ""),
                        media_urls=media[:1],
                    )
                )
        return out

    def _fetch_reddit(self, client: httpx.Client, source_cfg: dict[str, Any]) -> list[LiveItem]:
        out: list[LiveItem] = []
        subreddits = [str(x).strip() for x in source_cfg.get("subreddits", []) if str(x).strip()]
        sort = str(source_cfg.get("sort", "new"))
        limit = int(source_cfg.get("limit_per_subreddit", 10))
        max_subreddits = int(source_cfg.get("max_subreddits", 3))
        topic = str(source_cfg.get("topic", "ai"))
        headers = {"User-Agent": "catchdash/0.1 (+https://github.com/catchdash)"}

        for subreddit in subreddits[:max_subreddits]:
            res = client.get(
                f"https://www.reddit.com/r/{subreddit}/{sort}.json",
                params={"limit": limit},
                headers=headers,
            )
            res.raise_for_status()
            children = (res.json().get("data") or {}).get("children", [])
            for child in children:
                data = child.get("data") or {}
                created_utc = data.get("created_utc")
                if created_utc is None:
                    continue
                timestamp = dt.datetime.fromtimestamp(float(created_utc), tz=dt.UTC)
                permalink = str(data.get("permalink") or "")
                post_url = f"https://www.reddit.com{permalink}" if permalink else str(data.get("url") or "")
                preview = (data.get("preview") or {}).get("images") or []
                media_urls: list[str] = []
                if preview:
                    source = preview[0].get("source") or {}
                    if source.get("url"):
                        media_urls.append(html.unescape(str(source.get("url"))))
                out.append(
                    LiveItem(
                        source=str(source_cfg.get("source_id") or "reddit"),
                        topic=topic,
                        timestamp=timestamp,
                        raw_id=str(data.get("id") or permalink or post_url),
                        title=_trim(str(data.get("title") or "Reddit post"), 180),
                        text=_trim(str(data.get("selftext") or ""), 320),
                        author=str(data.get("author") or ""),
                        url=post_url,
                        media_urls=media_urls[:1],
                    )
                )
        return out

    def _fetch_hackernews(self, client: httpx.Client, source_cfg: dict[str, Any]) -> list[LiveItem]:
        out: list[LiveItem] = []
        queries = [str(x).strip() for x in source_cfg.get("queries", []) if str(x).strip()]
        hits_per_query = int(source_cfg.get("hits_per_query", 10))
        max_queries = int(source_cfg.get("max_queries", 4))
        topic = str(source_cfg.get("topic", "ai"))

        for query in queries[:max_queries]:
            res = client.get(
                "https://hn.algolia.com/api/v1/search_by_date",
                params={"query": query, "tags": "story", "hitsPerPage": hits_per_query},
            )
            res.raise_for_status()
            for row in res.json().get("hits", []):
                ts = row.get("created_at_i")
                if ts is None:
                    continue
                timestamp = dt.datetime.fromtimestamp(int(ts), tz=dt.UTC)
                object_id = str(row.get("objectID") or "")
                story_url = row.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
                out.append(
                    LiveItem(
                        source=str(source_cfg.get("source_id") or "hackernews"),
                        topic=topic,
                        timestamp=timestamp,
                        raw_id=object_id,
                        title=_trim(str(row.get("title") or "HN story"), 180),
                        text=_trim(str(row.get("story_text") or ""), 320),
                        author=str(row.get("author") or ""),
                        url=str(story_url),
                        media_urls=[],
                    )
                )
        return out

    def _fetch_bluesky_links(self, source_cfg: dict[str, Any]) -> list[LiveItem]:
        now = dt.datetime.now(dt.UTC)
        topic = str(source_cfg.get("topic", "ai"))
        out: list[LiveItem] = []
        urls = [str(x).strip() for x in source_cfg.get("profile_urls", []) if str(x).strip()]
        for idx, url in enumerate(urls[: int(source_cfg.get("max_links", 3))]):
            out.append(
                LiveItem(
                    source=str(source_cfg.get("source_id") or "bluesky"),
                    topic=topic,
                    timestamp=now,
                    raw_id=f"link-{idx}",
                    title=str(source_cfg.get("link_title", f"Open Bluesky ({topic})")),
                    text=str(source_cfg.get("link_text", "Browse latest Bluesky posts.")),
                    author="Bluesky",
                    url=url,
                    media_urls=[],
                )
            )
        return out

    def _fetch_bluesky_api(self, client: httpx.Client, source_cfg: dict[str, Any]) -> list[LiveItem]:
        out: list[LiveItem] = []
        base_url = str(source_cfg.get("base_url", "https://public.api.bsky.app")).rstrip("/")
        topic = str(source_cfg.get("topic", "ai"))
        limit = int(source_cfg.get("limit_per_request", 10))

        handles = [str(x).strip() for x in source_cfg.get("handles", []) if str(x).strip()]
        max_handles = int(source_cfg.get("max_handles", 3))
        queries = [str(x).strip() for x in source_cfg.get("queries", []) if str(x).strip()]
        max_queries = int(source_cfg.get("max_queries", 2))

        # Handle-based author feeds.
        for handle in handles[:max_handles]:
            try:
                did = self._resolve_bluesky_handle(client, base_url, handle)
                if not did:
                    continue
                res = client.get(
                    f"{base_url}/xrpc/app.bsky.feed.getAuthorFeed",
                    params={"actor": did, "limit": limit},
                )
                res.raise_for_status()
                for row in res.json().get("feed", []):
                    post = row.get("post") or {}
                    item = self._bluesky_post_to_item(post, source_cfg.get("source_id", "bluesky"), topic)
                    if item:
                        out.append(item)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("bluesky handle fetch failed handle=%s err=%s", handle, exc)

        # Query-based search feed (optional but useful when handles are sparse).
        if bool(source_cfg.get("enable_search", False)):
            for query in queries[:max_queries]:
                try:
                    res = client.get(
                        f"{base_url}/xrpc/app.bsky.feed.searchPosts",
                        params={"q": query, "limit": limit},
                    )
                    res.raise_for_status()
                    for post in res.json().get("posts", []):
                        item = self._bluesky_post_to_item(post, source_cfg.get("source_id", "bluesky"), topic)
                        if item:
                            out.append(item)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("bluesky query fetch failed query=%s err=%s", query, exc)

        return out

    def _resolve_bluesky_handle(self, client: httpx.Client, base_url: str, handle: str) -> str | None:
        res = client.get(
            f"{base_url}/xrpc/com.atproto.identity.resolveHandle",
            params={"handle": handle},
        )
        if res.status_code >= 400:
            return None
        did = str((res.json() or {}).get("did") or "").strip()
        return did or None

    def _bluesky_post_to_item(self, post: dict[str, Any], source_id: str, topic: str) -> LiveItem | None:
        if not isinstance(post, dict):
            return None
        author = post.get("author") or {}
        record = post.get("record") or {}
        text = str(record.get("text") or post.get("text") or "").strip()
        if not text:
            return None

        ts = (
            _parse_datetime(record.get("createdAt"))
            or _parse_datetime(post.get("indexedAt"))
            or _parse_datetime(post.get("createdAt"))
        )
        if not ts:
            return None

        raw_uri = str(post.get("uri") or "")
        handle = str(author.get("handle") or "").strip()
        open_url = self._bluesky_open_url(raw_uri, handle)
        if not open_url:
            return None

        media_urls = self._bluesky_media_urls(post)
        author_name = str(author.get("displayName") or author.get("handle") or "Bluesky")
        return LiveItem(
            source=str(source_id),
            topic=topic,
            timestamp=ts,
            raw_id=raw_uri or open_url,
            title=_trim(text, 120),
            text=_trim(text, 320),
            author=author_name,
            url=open_url,
            media_urls=media_urls[:1],
        )

    def _bluesky_open_url(self, uri: str, handle: str) -> str:
        # at://did:plc:xxx/app.bsky.feed.post/rkey -> https://bsky.app/profile/{handle}/post/{rkey}
        if uri.startswith("at://") and "/app.bsky.feed.post/" in uri and handle:
            rkey = uri.rsplit("/", 1)[-1]
            if rkey:
                return f"https://bsky.app/profile/{handle}/post/{rkey}"
        return ""

    def _bluesky_media_urls(self, post: dict[str, Any]) -> list[str]:
        out: list[str] = []
        embed = post.get("embed") or {}
        images = embed.get("images") or []
        for image in images:
            if not isinstance(image, dict):
                continue
            fullsize = str(image.get("fullsize") or "").strip()
            thumb = str(image.get("thumb") or "").strip()
            if fullsize:
                out.append(fullsize)
            elif thumb:
                out.append(thumb)
        return out

    def _live_cfg(self) -> dict[str, Any]:
        return load_live_social_config(settings.topics_config_path)

    def _sources_cfg(self) -> list[dict[str, Any]]:
        raw = self._live_cfg().get("sources")
        if not isinstance(raw, list):
            return []
        out: list[dict[str, Any]] = []
        for row in raw:
            if not isinstance(row, dict):
                continue
            source_id = str(row.get("source_id") or "").strip()
            if not source_id:
                continue
            merged = {"source_id": source_id, **row}
            out.append(merged)
        return out

    def _source_cfg(self, source_id: str) -> dict[str, Any] | None:
        for row in self._sources_cfg():
            if str(row.get("source_id")) == source_id:
                return row
        return None


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_datetime(value: Any) -> dt.datetime | None:
    if not value:
        return None
    if isinstance(value, dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=dt.UTC)
    text = str(value)
    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)
    except ValueError:
        return None


def _trim(value: str, n: int) -> str:
    txt = (value or "").strip()
    if len(txt) <= n:
        return txt
    return txt[: max(0, n - 1)].rstrip() + "…"


def _sort_key(value: Any) -> float:
    parsed = _parse_datetime(value)
    return parsed.timestamp() if parsed else 0.0


def _looks_english(value: str) -> bool:
    text = (value or "").strip().lower()
    if not text:
        return False

    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"#\w+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return False

    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    ascii_ratio = sum(1 for c in letters if "a" <= c <= "z") / len(letters)
    if ascii_ratio < 0.85:
        return False

    tokens = re.findall(r"[a-z]+", text)
    if len(tokens) < 3:
        return ascii_ratio >= 0.95

    common_en = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "you",
        "your",
        "have",
        "will",
        "new",
        "today",
        "about",
        "news",
        "ai",
        "model",
        "openai",
    }
    english_hits = sum(1 for t in tokens if t in common_en)
    return english_hits >= 1


live_social_service = LiveSocialService()
