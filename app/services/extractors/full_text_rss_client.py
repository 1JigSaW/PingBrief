from __future__ import annotations

import os
from typing import Optional

import requests


class FullTextRssClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: int = 20,
    ) -> None:
        self.base_url = base_url or os.getenv("FULL_TEXT_RSS_BASE_URL", "http://fulltextrss:80")
        self.timeout_seconds = timeout_seconds
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def extract(
        self,
        url: str,
    ) -> Optional[str]:
        try:
            resp = requests.get(
                f"{self.base_url}/makefulltextfeed",
                params={
                    "url": url,
                    "format": "txt",
                    "max": 1,
                },
                headers=self.headers,
                timeout=self.timeout_seconds,
            )
            if not resp.ok:
                return None
            text = (resp.text or "").strip()
            if text:
                return " ".join(text.split())
            return None
        except Exception:
            return None


