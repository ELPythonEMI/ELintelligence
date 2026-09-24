from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup


@dataclass
class WebResult:
    title: str
    url: str
    description: str


class WebSearch:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
            )
        })

    @staticmethod
    def _clean_ddg_url(url: str) -> str:
        if url.startswith("//"):
            url = "https:" + url
        try:
            parsed = urlparse(url)
            if "duckduckgo.com" in parsed.netloc:
                value = parse_qs(parsed.query).get("uddg", [None])[0]
                if value:
                    return value
        except Exception:
            pass
        return url

    def direct(self, query: str, limit: int = 5) -> list[WebResult]:
        response = self.session.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query, "kl": "it-it"},
            timeout=(15, 25),
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        results: list[WebResult] = []
        for block in soup.select(".result"):
            anchor = block.select_one("a.result__a")
            if not anchor:
                continue
            title = anchor.get_text(" ", strip=True)
            url = self._clean_ddg_url(anchor.get("href", "").strip())
            snippet_node = block.select_one(".result__snippet")
            snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
            if title and url.startswith(("http://", "https://")):
                results.append(WebResult(title=title, url=url, description=snippet))
            if len(results) >= limit:
                break

        if not results:
            # Fallback deliberately conservative: only external HTTP links.
            for anchor in soup.find_all("a", href=True):
                url = self._clean_ddg_url(anchor["href"].strip())
                title = anchor.get_text(" ", strip=True)
                if title and url.startswith(("http://", "https://")) and "duckduckgo.com" not in url:
                    results.append(WebResult(title=title, url=url, description=""))
                if len(results) >= limit:
                    break
        return results

    def brave(self, query: str, api_key: str, limit: int = 5) -> list[WebResult]:
        response = self.session.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={
                "q": query,
                "count": min(20, limit),
                "country": "IT",
                "search_lang": "it",
                "ui_lang": "it-IT",
                "safesearch": "moderate",
            },
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": api_key,
            },
            timeout=(15, 25),
        )
        response.raise_for_status()
        raw = response.json()
        items = raw.get("web", {}).get("results", [])
        results: list[WebResult] = []
        for item in items[:limit]:
            url = str(item.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                continue
            results.append(WebResult(
                title=str(item.get("title") or url),
                url=url,
                description=str(item.get("description") or ""),
            ))
        return results
