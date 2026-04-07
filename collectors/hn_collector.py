"""
Hacker News Algolia API Collector
- 무료, 인증 불필요
- https://hn.algolia.com/api
"""

import time
import json
import requests
from datetime import datetime

KEYWORDS = ["aws", "claude", "openai", "azure", "llm", "anthropic"]

BASE_URL = "http://hn.algolia.com/api/v1/search_by_date?query={query}&tags=story&hitsPerPage=20"

HEADERS = {
    "User-Agent": "trend-validator/1.0",
}


def fetch_keyword(keyword: str) -> list[dict]:
    url = BASE_URL.format(query=keyword)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", [])
        result = []
        for hit in hits:
            created_at = hit.get("created_at", "")
            result.append({
                "source": "hn",
                "keyword": keyword,
                "title": hit.get("title", ""),
                "url": hit.get("url", "") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "published_at": created_at,
                "author": hit.get("author", ""),
                "points": hit.get("points", 0),
                "num_comments": hit.get("num_comments", 0),
                "objectID": hit.get("objectID", ""),
            })
        return result
    except Exception as e:
        print(f"  [WARN] HN fetch failed for '{keyword}': {e}")
        return []


def collect() -> dict:
    print("[HN] 수집 시작...")
    all_items = []
    seen_ids = set()

    for keyword in KEYWORDS:
        print(f"  -> 키워드: '{keyword}'")
        items = fetch_keyword(keyword)
        deduped = []
        for item in items:
            oid = item.get("objectID", "")
            if oid and oid in seen_ids:
                continue
            seen_ids.add(oid)
            deduped.append(item)
        all_items.extend(deduped)
        print(f"     {len(deduped)}개 수집 (중복 제거 후, 원본 {len(items)}개)")
        time.sleep(2)

    result = {
        "source": "hn",
        "collected_at": datetime.utcnow().isoformat() + "Z",
        "total": len(all_items),
        "items": all_items,
    }
    print(f"[HN] 완료: 총 {len(all_items)}개")
    return result


if __name__ == "__main__":
    data = collect()
    print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
