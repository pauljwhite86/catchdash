from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup


def extract_main_text(url: str, timeout_seconds: float = 20.0) -> str:
    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        res = client.get(url)
        res.raise_for_status()
        html = res.text

    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'noscript', 'header', 'footer']):
        tag.extract()

    root = _pick_best_root(soup)
    chunks = _collect_chunks(root)

    joined = '\n'.join(chunks)
    joined = re.sub(r'\s+', ' ', joined).strip()
    return joined


def _pick_best_root(soup: BeautifulSoup):
    # Prefer explicit article body semantics where available.
    semantic = soup.select_one('[itemprop="articleBody"]')
    if semantic is not None:
        return semantic

    # Some publishers include multiple article blocks; choose by text density.
    candidates = soup.find_all('article')
    if candidates:
        scored = sorted(candidates, key=lambda node: len(_collect_chunks(node)), reverse=True)
        if scored and len(_collect_chunks(scored[0])) > 0:
            return scored[0]

    # Common fallback containers.
    for selector in ('main', '.body-text', '.post__col', '.entry-content', '.article-body'):
        found = soup.select_one(selector)
        if found is not None and len(_collect_chunks(found)) > 0:
            return found

    return soup


def _collect_chunks(root) -> list[str]:
    chunks: list[str] = []
    for node in root.find_all(['h1', 'h2', 'h3', 'p', 'li']):
        text = node.get_text(' ', strip=True)
        if text and len(text) > 20:
            chunks.append(text)
    return chunks
