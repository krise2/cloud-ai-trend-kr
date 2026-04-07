"""
run_all.py — 모든 수집기를 순차 실행하고 data/ 에 결과를 저장한다.

출력 파일:
    data/github.json
    data/youtube.json
    data/reddit.json
    data/hn.json
    data/latest.json  — 4개 소스 통합, 중복 제거, 시간순 정렬, 최신 200건
    data/last_updated.txt — 수집 완료 시각 (KST ISO8601)
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

# collectors 패키지 경로를 sys.path 에 추가 (어디서 실행해도 동작)
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(ROOT / "collectors"))

import github_collector
import youtube_collector
import reddit_collector
import hn_collector

KST = timezone(timedelta(hours=9))


# ── 정규화 헬퍼 ──────────────────────────────────────────────
def normalize(item: dict, source: str) -> dict:
    """소스별 아이템을 공통 스키마로 변환한다."""
    title = item.get("title", "")
    url = (
        item.get("url")
        or item.get("permalink")
        or ""
    )
    published_at = item.get("published_at", "")
    score = (
        item.get("score")
        or item.get("points")
        or item.get("stars")  # github trending — 문자열일 수 있음
        or 0
    )
    # stars 필드가 문자열("1,234")이면 숫자로 변환 시도
    if isinstance(score, str):
        try:
            score = int(score.replace(",", "").strip())
        except ValueError:
            score = 0

    return {
        "source": source,
        "title": title,
        "url": url,
        "published_at": published_at,
        "score": score,
        "summary_ko": None,  # 에이전트가 나중에 채울 필드
    }


def parse_dt(published_at: str) -> datetime:
    """ISO8601 문자열을 datetime 으로 파싱. 실패 시 epoch 반환."""
    if not published_at:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S+00:00",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            dt = datetime.strptime(published_at[:26], fmt[:len(fmt)])
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


# ── 수집기 실행 ──────────────────────────────────────────────
def run_collector(name: str, module) -> dict:
    print(f"\n{'='*50}")
    print(f"  {name} 수집 시작")
    print(f"{'='*50}")
    t0 = time.time()
    try:
        result = module.collect()
    except Exception as e:
        print(f"  [ERROR] {name} 수집 실패: {e}")
        result = {
            "source": name,
            "collected_at": datetime.utcnow().isoformat() + "Z",
            "total": 0,
            "items": [],
        }
    elapsed = time.time() - t0
    print(f"  [{name}] 소요시간: {elapsed:.1f}s / 수집: {result.get('total', 0)}건")
    return result


def main():
    start = time.time()
    print(f"\n[run_all] 수집 시작: {datetime.now(KST).isoformat()}")

    collectors = [
        ("github",  github_collector),
        ("youtube", youtube_collector),
        ("reddit",  reddit_collector),
        ("hn",      hn_collector),
    ]

    all_normalized = []
    counts = {}

    for name, module in collectors:
        result = run_collector(name, module)

        # 소스별 JSON 저장
        out_path = DATA_DIR / f"{name}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  -> 저장: {out_path}")

        # 정규화 후 통합 목록에 추가
        for item in result.get("items", []):
            all_normalized.append(normalize(item, name))

        counts[name] = result.get("total", 0)

    # ── latest.json 생성 ──────────────────────────────────────
    # 1) URL 기준 중복 제거
    seen_urls: set[str] = set()
    deduped = []
    for item in all_normalized:
        url = item["url"]
        if url and url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(item)

    # 2) published_at 내림차순 정렬 (최신 → 과거)
    deduped.sort(key=lambda x: parse_dt(x["published_at"]), reverse=True)

    # 3) 최신 200건
    latest = deduped[:200]

    latest_path = DATA_DIR / "latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(latest, f, ensure_ascii=False, indent=2)
    print(f"\n  -> latest.json 저장: {len(latest)}건 (중복 제거 후 {len(deduped)}건 중 상위 200)")

    # ── last_updated.txt ─────────────────────────────────────
    now_kst = datetime.now(KST).isoformat()
    updated_path = DATA_DIR / "last_updated.txt"
    updated_path.write_text(now_kst + "\n", encoding="utf-8")

    # ── 최종 요약 ─────────────────────────────────────────────
    elapsed_total = time.time() - start
    print(f"\n{'='*50}")
    print(f"  [완료] 총 소요시간: {elapsed_total:.1f}s")
    print(f"  last_updated: {now_kst}")
    print("  소스별 수집 건수:")
    for name, cnt in counts.items():
        print(f"    {name:10s}: {cnt}건")
    print(f"  latest.json  : {len(latest)}건")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
