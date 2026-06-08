#!/usr/bin/env python3
"""
feed_decantika.py
Fetches Decantika's native Shopify Atom feed for the "All Clones, Designers
& Niche Copy" collection and re-publishes it as feed_decantika.xml (RSS 2.0).

Source: https://decantika.com/collections/all-clones-designers-niche-copy.atom

Dependencies: requests
  pip install requests
"""

import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import formatdate

import requests

SOURCE_FEED = (
    "https://decantika.com/collections/all-clones-designers-niche-copy.atom"
)
SITE_URL = "https://decantika.com/collections/all-clones-designers-niche-copy"
FEED_NAME = "decantika"
OUTPUT_FILE = f"feed_{FEED_NAME}.xml"
SELF_LINK = (
    f"https://raw.githubusercontent.com/itsreese83/Decantika/main/{OUTPUT_FILE}"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

ATOM_NS = "{http://www.w3.org/2005/Atom}"


def fetch_feed(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def escape_xml(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&apos;")
    )


def to_rfc822(dt: datetime) -> str:
    return formatdate(dt.timestamp(), usegmt=True)


def parse_atom_date(value: str) -> datetime:
    if value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    return datetime.now(tz=timezone.utc)


def parse_feed(xml_text: str) -> list[dict]:
    """Parse the upstream Shopify Atom feed into a list of product dicts."""
    root = ET.fromstring(xml_text)

    products = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        def text(tag: str) -> str:
            el = entry.find(f"{ATOM_NS}{tag}")
            return (el.text or "").strip() if el is not None else ""

        title = text("title")
        product_id = text("id")
        published = text("published") or text("updated")
        summary = text("summary")
        content = text("content")

        link = ""
        link_el = entry.find(f"{ATOM_NS}link")
        if link_el is not None:
            link = link_el.get("href", "")

        if not title or not link:
            continue

        pub_dt = parse_atom_date(published)
        description = content or summary

        products.append(
            {
                "title": title,
                "link": link,
                "guid": product_id or link,
                "pub_dt": pub_dt,
                "description": description,
            }
        )

    return products


def build_rss(products: list[dict]) -> str:
    now_rfc = to_rfc822(datetime.now(tz=timezone.utc))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        "    <title>Decantika — All Clones, Designers &amp; Niche Copy</title>",
        f"    <link>{escape_xml(SITE_URL)}</link>",
        "    <description>Latest clone/designer/niche copy decant listings at Decantika</description>",
        "    <language>en-us</language>",
        f"    <lastBuildDate>{now_rfc}</lastBuildDate>",
        f'    <atom:link href="{SELF_LINK}" rel="self" type="application/rss+xml"/>',
    ]

    for d in products:
        lines += [
            "    <item>",
            f"      <title>{escape_xml(d['title'])}</title>",
            f"      <link>{escape_xml(d['link'])}</link>",
            f"      <guid isPermaLink=\"false\">{escape_xml(d['guid'])}</guid>",
            f"      <pubDate>{to_rfc822(d['pub_dt'])}</pubDate>",
        ]
        if d["description"]:
            lines.append(f"      <description><![CDATA[{d['description']}]]></description>")
        lines.append("    </item>")

    lines += ["  </channel>", "</rss>"]
    return "\n".join(lines)


def main() -> None:
    print("Fetching Decantika All Clones / Designers / Niche Copy feed …")
    xml_text = fetch_feed(SOURCE_FEED)

    print("Parsing feed …")
    products = parse_feed(xml_text)
    print(f"  Found {len(products)} products.")

    if not products:
        print("ERROR: No products found in upstream feed.", file=sys.stderr)
        sys.exit(1)

    rss = build_rss(products)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(rss)

    print(f"Written → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
