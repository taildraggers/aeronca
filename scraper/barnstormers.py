"""Scraper for Aeronca aircraft listings on barnstormers.com."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import Listing, extract_date, extract_location, extract_price, fetch

SITE_NAME = "Barnstormers.com"
BASE = "https://www.barnstormers.com"

# (main category, sub category) pairs that carry Aeronca listings on Barnstormers.
SEARCHES = [
    ("Antique-Classic", "Aeronca"),
    ("Light-Sport", "Aeronca"),
    ("Experimental", "Aeronca"),
]

MAX_PAGES = 10
LISTING_LINK_RE = re.compile(r"^/classified-\d+-.*\.html$")


def _list_page_url(main: str, sub: str, page: int) -> str:
    url = f"{BASE}/ad_manager/listing.php?main={main}&sub={sub}"
    if page > 1:
        url += f"&page={page}"
    return url


def _find_listing_links(html: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if LISTING_LINK_RE.match(href):
            links.add(urljoin(BASE, href))
    return links


def _debug_dump_hrefs(html: str, limit: int = 25) -> None:
    soup = BeautifulSoup(html, "lxml")
    hrefs = [a["href"] for a in soup.find_all("a", href=True)]
    interesting = [h for h in hrefs if "classified" in h.lower() or "aeronca" in h.lower()]
    sample = interesting[:limit] or hrefs[:limit]
    print(f"  [debug] {len(hrefs)} total <a href> on page; sample: {sample}")


def _parse_detail_page(url: str, html: str) -> Listing | None:
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None
    if not title:
        return None
    title = re.sub(r"\s*[\|\-]\s*Barnstormers.*$", "", title, flags=re.IGNORECASE).strip()

    text = soup.get_text(" ", strip=True)
    price = extract_price(text)
    location = extract_location(text)
    date_posted = extract_date(text)

    return Listing(
        title=title,
        price=price,
        location=location,
        date_posted=date_posted,
        site=SITE_NAME,
        url=url,
    )


def scrape() -> list[Listing]:
    print(f"[{SITE_NAME}] starting scrape")
    all_links: set[str] = set()

    for main, sub in SEARCHES:
        seen_this_search: set[str] = set()
        for page in range(1, MAX_PAGES + 1):
            url = _list_page_url(main, sub, page)
            html = fetch(url)
            if not html:
                break
            links = _find_listing_links(html)
            new_links = links - seen_this_search
            print(f"  [{main}/{sub}] page {page}: {len(links)} links ({len(new_links)} new)")
            if page == 1 and not links:
                _debug_dump_hrefs(html)
            if not links or not new_links:
                break
            seen_this_search |= links
        all_links |= seen_this_search

    print(f"[{SITE_NAME}] {len(all_links)} unique listing URLs found")

    listings: list[Listing] = []
    for url in sorted(all_links):
        html = fetch(url)
        if not html:
            continue
        listing = _parse_detail_page(url, html)
        if listing:
            listings.append(listing)

    print(f"[{SITE_NAME}] parsed {len(listings)} listings")
    return listings
