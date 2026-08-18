"""Scraper for Aeronca aircraft listings on controller.com."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .common import (
    Listing,
    extract_date,
    extract_jsonld_objects,
    extract_location,
    extract_price,
    fetch,
)

SITE_NAME = "Controller.com"
BASE = "https://www.controller.com"
LIST_URL = f"{BASE}/listings/for-sale/aeronca/aircraft"
MAX_PAGES = 10

# Detail page URLs look like /listing/for-sale/<slug>/<numeric-id> - be
# permissive since the exact slug format can vary by category.
LISTING_LINK_RE = re.compile(r"^/listing/for-sale/[^/]+/\d+/?$")


def _list_page_url(page: int) -> str:
    return LIST_URL if page == 1 else f"{LIST_URL}/{page}"


def _find_listing_links(html: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0]
        if LISTING_LINK_RE.match(href):
            links.add(urljoin(BASE, href))
    return links


def _debug_dump_hrefs(html: str, limit: int = 25) -> None:
    soup = BeautifulSoup(html, "lxml")
    hrefs = [a["href"] for a in soup.find_all("a", href=True)]
    interesting = [h for h in hrefs if "listing" in h.lower()]
    sample = interesting[:limit] or hrefs[:limit]
    print(f"  [debug] {len(hrefs)} total <a href> on page; sample: {sample}")


def _parse_detail_page(url: str, html: str) -> Listing | None:
    soup = BeautifulSoup(html, "lxml")

    title = None
    price = None
    date_posted = ""

    for obj in extract_jsonld_objects(soup):
        if not title and isinstance(obj.get("name"), str):
            title = obj["name"]
        offers = obj.get("offers")
        if isinstance(offers, dict) and not price and offers.get("price"):
            price = f"${offers['price']}"
        if not date_posted:
            for key in ("datePosted", "dateCreated", "datePublished"):
                if obj.get(key):
                    date_posted = str(obj[key])
                    break

    if not title:
        title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None
        if title:
            title = re.sub(r"\s*[\|\-]\s*Controller\.com.*$", "", title, flags=re.IGNORECASE).strip()
    if not title:
        return None

    text = soup.get_text(" ", strip=True)
    if not price:
        price = extract_price(text)
    location = extract_location(text)
    if not date_posted:
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

    for page in range(1, MAX_PAGES + 1):
        url = _list_page_url(page)
        html = fetch(url)
        if not html:
            break
        links = _find_listing_links(html)
        new_links = links - all_links
        print(f"  page {page}: {len(links)} links ({len(new_links)} new)")
        if page == 1 and not links:
            _debug_dump_hrefs(html)
        if not links or not new_links:
            break
        all_links |= links

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
