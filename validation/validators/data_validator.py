"""
Data Validator
- 수집된 데이터 품질 지표 계산
"""

from datetime import datetime, timezone
from collections import Counter

CLOUD_AI_KEYWORDS = [
    "aws", "azure", "gcp", "google cloud", "cloud",
    "ai", "ml", "llm", "gpt", "claude", "openai", "anthropic",
    "machine learning", "deep learning", "neural", "transformer",
    "bedrock", "sagemaker", "vertex", "copilot", "gemini",
    "langchain", "llama", "mistral", "ollama", "hugging face",
    "kubernetes", "docker", "serverless", "lambda", "s3",
    "chatgpt", "diffusion", "rag", "vector",
    # GitHub trending용 — repo path/description 매칭
    "python", "typescript", "rust", "agent", "model", "inference",
    "api", "sdk", "framework", "tool", "deploy", "platform",
    "data", "pipeline", "automation", "script", "service",
]


def parse_dt(dt_str: str):
    if not dt_str:
        return None
    # ISO 8601 정규화: 마이크로초 제거 후 파싱
    s = dt_str.strip()
    # Z를 +00:00으로 통일
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    # 마이크로초 제거 (소수점 이하 6자리 -> 3자리로 truncate)
    import re
    s = re.sub(r'(\.\d{3})\d+', r'\1', s)
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%f+00:00",
        "%Y-%m-%dT%H:%M:%S+00:00",
        "%Y-%m-%dT%H:%M:%S",
    ]:
        try:
            return datetime.strptime(s[:len(fmt)+2], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    # 최후 수단: dateutil 없이 앞 19자만 파싱
    try:
        return datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def validate(source_name: str, items: list[dict]) -> dict:
    total = len(items)
    if total == 0:
        return {
            "source": source_name,
            "total": 0,
            "duplicate_url_ratio": 0.0,
            "freshness_7d_ratio": 0.0,
            "empty_title_ratio": 0.0,
            "empty_url_ratio": 0.0,
            "keyword_relevance_ratio": 0.0,
            "issues": ["no data collected"],
        }

    # 중복 URL
    urls = [item.get("url", "") for item in items]
    url_counts = Counter(urls)
    duplicate_count = sum(cnt - 1 for cnt in url_counts.values() if cnt > 1)
    duplicate_ratio = round(duplicate_count / total, 4)

    # Freshness (7일 이내)
    now = datetime.now(timezone.utc)
    fresh_count = 0
    unparseable_dt = 0
    for item in items:
        dt = parse_dt(item.get("published_at", ""))
        if dt is None:
            unparseable_dt += 1
            continue
        delta = now - dt
        if delta.days <= 7:
            fresh_count += 1
    freshness_ratio = round(fresh_count / total, 4)

    # 빈 title/url
    empty_title = sum(1 for item in items if not item.get("title", "").strip())
    empty_url = sum(1 for item in items if not item.get("url", "").strip())
    empty_title_ratio = round(empty_title / total, 4)
    empty_url_ratio = round(empty_url / total, 4)

    # 키워드 관련성 (title + description + repo + keyword 필드 모두 검색)
    relevant_count = 0
    for item in items:
        combined = " ".join([
            item.get("title", ""),
            item.get("description", ""),
            item.get("repo", ""),
            item.get("keyword", ""),
            item.get("subreddit", ""),
            item.get("channel", ""),
        ]).lower()
        if any(kw in combined for kw in CLOUD_AI_KEYWORDS):
            relevant_count += 1
    relevance_ratio = round(relevant_count / total, 4)

    issues = []
    if duplicate_ratio > 0.1:
        issues.append(f"높은 중복 비율: {duplicate_ratio:.1%}")
    if freshness_ratio < 0.3:
        issues.append(f"낮은 신선도 (7일 이내): {freshness_ratio:.1%}")
    if empty_title_ratio > 0.05:
        issues.append(f"빈 title 비율 높음: {empty_title_ratio:.1%}")
    if empty_url_ratio > 0.05:
        issues.append(f"빈 url 비율 높음: {empty_url_ratio:.1%}")
    if relevance_ratio < 0.3:
        issues.append(f"낮은 관련성 점수: {relevance_ratio:.1%}")
    if unparseable_dt > 0:
        issues.append(f"날짜 파싱 불가 항목: {unparseable_dt}개")

    return {
        "source": source_name,
        "total": total,
        "duplicate_url_ratio": duplicate_ratio,
        "freshness_7d_ratio": freshness_ratio,
        "empty_title_ratio": empty_title_ratio,
        "empty_url_ratio": empty_url_ratio,
        "keyword_relevance_ratio": relevance_ratio,
        "issues": issues if issues else ["이상 없음"],
    }
