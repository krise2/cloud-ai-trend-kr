"""
YouTube RSS Collector
- API 없이 채널 RSS 피드 사용
- feedparser 또는 xml.etree로 파싱
"""

import time
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

CHANNELS = {
    "AWS": "UCVHVbLlEjAGBfKEMRfqgAoQ",
    "Microsoft_Azure": "UC0m-80FnNY2Qb7obvTL_2fA",
    "Google_Cloud": "UCJS9pqu9BzkAMNTmzNMNhvg",
    "freeCodeCamp": "UC8butISFwT-Wl7EV0hUK0BQ",
}

RSS_BASE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

HEADERS = {
    "User-Agent": "trend-validator/1.0",
    "Accept": "application/atom+xml,application/xml,text/xml",
}

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}


def parse_feed(xml_text: str, channel_name: str, limit: int = 10) -> list[dict]:
    try:
        root = ET.fromstring(xml_text)
        entries = root.findall("atom:entry", NS)
        result = []
        for entry in entries[:limit]:
            title_el = entry.find("atom:title", NS)
            link_el = entry.find("atom:link", NS)
            published_el = entry.find("atom:published", NS)
            author_el = entry.find("atom:author/atom:name", NS)

            title = title_el.text if title_el is not None else ""
            url = link_el.get("href", "") if link_el is not None else ""
            published_at = published_el.text if published_el is not None else ""
            author = author_el.text if author_el is not None else channel_name

            result.append({
                "source": "youtube_rss",
                "channel": channel_name,
                "title": title,
                "url": url,
                "published_at": published_at,
                "author": author,
            })
        return result
    except Exception as e:
        print(f"  [WARN] XML parse error for {channel_name}: {e}")
        return []


def fetch_channel(channel_name: str, channel_id: str, limit: int = 10) -> list[dict]:
    url = RSS_BASE.format(channel_id=channel_id)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        items = parse_feed(resp.text, channel_name, limit)
        return items
    except Exception as e:
        print(f"  [WARN] YouTube RSS fetch failed for {channel_name}: {e}")
        return []


def collect() -> dict:
    print("[YouTube] 수집 시작...")
    all_items = []

    for channel_name, channel_id in CHANNELS.items():
        print(f"  -> 채널: {channel_name} ({channel_id})")
        items = fetch_channel(channel_name, channel_id, limit=10)
        all_items.extend(items)
        print(f"     {len(items)}개 수집")
        time.sleep(2)

    result = {
        "source": "youtube",
        "collected_at": datetime.utcnow().isoformat() + "Z",
        "total": len(all_items),
        "items": all_items,
    }
    print(f"[YouTube] 완료: 총 {len(all_items)}개")
    return result


if __name__ == "__main__":
    data = collect()
    print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
