from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup


def clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", value).strip()
    return text or None


def get_page_title(soup: BeautifulSoup) -> str:
    for tag_name in ("h1", "h2", "title"):
        tag = soup.find(tag_name)
        if tag:
            return clean_text(tag.get_text(" ", strip=True)) or ""
    return ""
