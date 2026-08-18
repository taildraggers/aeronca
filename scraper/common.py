"""Shared helpers used by the Aeronca listing scrapers."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "AeroncaListingsBot/1.0 (+https://github.com/taildraggers/aeronca; "
    "daily aggregator of publicly listed Aeronca ads for taildraggers.com; "
    "contact via repo issues)"
)

REQUEST_TIMEOUT = 20
REQUEST_DELAY_SECONDS = 1.0

_session = requests.Session()
_session.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
)


def fetch(url: str) -> Optional[str]:
    """GET a URL and return its text, or None on failure. Adds a polite delay."""
    try:
        resp = _session.get(url, timeout=REQUEST_TIMEOUT)
        time.sleep(REQUEST_DELAY_SECONDS)
        if resp.status_code != 200:
            print(f"  [warn] {url} -> HTTP {resp.status_code}")
            return None
        return resp.text
    except requests.RequestException as exc:
        print(f"  [warn] {url} -> {exc}")
        return None


PRICE_RE = re.compile(r"\$\s?[\d,]{3,12}(?:\.\d{2})?")
STATE_ABBRS = (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT "
    "NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC"
).split()
LOCATION_RE = re.compile(
    r"\b([A-Z][a-zA-Z.'\-]+(?:\s[A-Z][a-zA-Z.'\-]+)*),\s(" + "|".join(STATE_ABBRS) + r")\b"
)
DATE_LABEL_RE = re.compile(
    r"(?:Date Posted|Date Listed|Posted|Listed)[:\s]+"
    r"([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)


def extract_price(text: str) -> str:
    m = PRICE_RE.search(text)
    return m.group(0).strip() if m else "Contact for price"


def extract_location(text: str) -> str:
    m = LOCATION_RE.search(text)
    return f"{m.group(1)}, {m.group(2)}" if m else "Unknown"


def extract_date(text: str) -> str:
    m = DATE_LABEL_RE.search(text)
    return m.group(1).strip() if m else ""


def extract_jsonld_objects(soup: BeautifulSoup) -> list[dict]:
    """Pull every schema.org JSON-LD object out of a page, if any are present."""
    objects: list[dict] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (ValueError, TypeError):
            continue
        if isinstance(data, list):
            objects.extend(d for d in data if isinstance(d, dict))
        elif isinstance(data, dict):
            objects.append(data)
    return objects


@dataclass
class Listing:
    title: str
    price: str
    location: str
    date_posted: str
    site: str
    url: str

    def key(self) -> tuple:
        return (self.site, self.url)
