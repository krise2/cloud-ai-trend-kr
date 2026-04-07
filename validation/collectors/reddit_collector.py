"""
Reddit JSON API Collector
- 인증 없이 공개 JSON API 사용
- User-Agent 필수 설정
"""

import time
import json
import requests
from datetime import datetime

SUBREDDITS = ["aws", "AZURE", "MachineLearning", "LocalLLaMA", "ClaudeAI", "ChatGPT"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 trend-validator/1.0",
    "Accept": "application/json",
}

BASE_URL = "https://www.reddit.com/r/{subreddit}/hot.json?limit=25"


def fetch_subreddit(subreddit: str) -> list[dict]:
    url = BASE_URL.format(subreddit=subreddit)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        posts = data.get("data", {}).get("children", [])
        result = []
        for post in posts:
            p = post.get("data", {})
            result.append({
                "source": "reddit",
                "subreddit": p.get("subreddit", subreddit),
                "title": p.get("title", ""),
                "url": p.get("url", ""),
                "permalink": "https://www.reddit.com" + p.get("permalink", ""),
                "score": p.get("score", 0),
                "num_comments": p.get("num_comments", 0),
                "created_utc": p.get("created_utc", 0),
                "published_at": datetime.utcfromtimestamp(
                    p.get("created_utc", 0)
                ).isoformat() + "Z",
                "author": p.get("author", ""),
            })
        return result
    except Exception as e:
        print(f"  [WARN] Reddit fetch failed for r/{subreddit}: {e}")
        return []


def collect() -> dict:
    print("[Reddit] 수집 시작...")
    all_items = []

    for subreddit in SUBREDDITS:
        print(f"  -> r/{subreddit}")
        items = fetch_subreddit(subreddit)
        all_items.extend(items)
        print(f"     {len(items)}개 수집")
        time.sleep(2)

    result = {
        "source": "reddit",
        "collected_at": datetime.utcnow().isoformat() + "Z",
        "total": len(all_items),
        "items": all_items,
    }
    print(f"[Reddit] 완료: 총 {len(all_items)}개")
    return result


if __name__ == "__main__":
    data = collect()
    print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
