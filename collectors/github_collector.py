"""
GitHub Collector
- 공식 릴리즈: GitHub REST API (인증 없이 60req/hr, GITHUB_TOKEN 있으면 5000req/hr)
- GitHub Trending: HTML 스크래핑
"""

import os
import time
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

REPOS = [
    "anthropics/claude-code",
    "openai/openai-python",
    "openai/whisper",
    "aws/aws-cdk",
    "microsoft/autogen",
    "microsoft/semantic-kernel",
    "langchain-ai/langchain",
    "run-llama/llama_index",
]

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "trend-validator/1.0",
}

TOKEN = os.environ.get("GITHUB_TOKEN")
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def fetch_releases(repo: str, per_page: int = 5) -> list[dict]:
    url = f"https://api.github.com/repos/{repo}/releases?per_page={per_page}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        releases = resp.json()
        result = []
        for r in releases:
            result.append({
                "source": "github_release",
                "repo": repo,
                "title": r.get("name") or r.get("tag_name", ""),
                "url": r.get("html_url", ""),
                "published_at": r.get("published_at", ""),
                "tag": r.get("tag_name", ""),
                "body_excerpt": (r.get("body") or "")[:300],
            })
        return result
    except Exception as e:
        print(f"  [WARN] GitHub releases fetch failed for {repo}: {e}")
        return []


def fetch_trending() -> list[dict]:
    url = "https://github.com/trending"
    try:
        resp = requests.get(url, headers={"User-Agent": "trend-validator/1.0"}, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        articles = soup.select("article.Box-row")
        result = []
        for article in articles[:30]:
            h2 = article.select_one("h2 a")
            if not h2:
                continue
            path = h2.get("href", "").strip("/")
            description_tag = article.select_one("p")
            description = description_tag.get_text(strip=True) if description_tag else ""
            stars_tag = article.select_one("a[href$='/stargazers']")
            stars = stars_tag.get_text(strip=True) if stars_tag else ""
            result.append({
                "source": "github_trending",
                "repo": path,
                "title": path,
                "url": f"https://github.com/{path}",
                "description": description,
                "stars": stars,
                "published_at": datetime.utcnow().isoformat() + "Z",
            })
        return result
    except Exception as e:
        print(f"  [WARN] GitHub trending fetch failed: {e}")
        return []


def collect() -> dict:
    print("[GitHub] 수집 시작...")
    all_items = []

    for repo in REPOS:
        print(f"  -> releases: {repo}")
        releases = fetch_releases(repo)
        all_items.extend(releases)
        print(f"     {len(releases)}개 수집")
        time.sleep(2)

    print("  -> GitHub Trending 스크래핑...")
    trending = fetch_trending()
    all_items.extend(trending)
    print(f"     {len(trending)}개 수집")

    result = {
        "source": "github",
        "collected_at": datetime.utcnow().isoformat() + "Z",
        "total": len(all_items),
        "items": all_items,
    }
    print(f"[GitHub] 완료: 총 {len(all_items)}개")
    return result


if __name__ == "__main__":
    data = collect()
    print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
