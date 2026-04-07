"""
run_validation.py
- 모든 collector 순차 실행
- 결과를 validation_results/ 에 JSON으로 저장
- 터미널에 요약 리포트 출력
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
RESULTS_DIR = BASE_DIR / "validation_results"
RESULTS_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(Path(__file__).parent))

from collectors.github_collector import collect as collect_github
from collectors.youtube_collector import collect as collect_youtube
from collectors.reddit_collector import collect as collect_reddit
from collectors.hn_collector import collect as collect_hn
from validators.data_validator import validate


def save_json(data: dict, filename: str):
    path = RESULTS_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  저장 완료: {path}")


def print_report(validations: list[dict]):
    print("\n" + "=" * 60)
    print("  데이터 소스 품질 검증 리포트")
    print(f"  실행 시각: {datetime.utcnow().isoformat()}Z")
    print("=" * 60)

    for v in validations:
        print(f"\n[{v['source'].upper()}]")
        print(f"  총 수집 건수     : {v['total']:,}개")
        print(f"  중복 URL 비율    : {v['duplicate_url_ratio']:.1%}")
        print(f"  7일 이내 (신선도): {v['freshness_7d_ratio']:.1%}")
        print(f"  빈 title 비율    : {v['empty_title_ratio']:.1%}")
        print(f"  빈 URL 비율      : {v['empty_url_ratio']:.1%}")
        print(f"  키워드 관련성    : {v['keyword_relevance_ratio']:.1%}")
        print(f"  품질 이슈        : {', '.join(v['issues'])}")

    print("\n" + "=" * 60)
    total_all = sum(v["total"] for v in validations)
    print(f"  전체 수집 합계: {total_all:,}개")
    print("=" * 60 + "\n")


def main():
    print("\n트렌드 데이터 소스 검증 시작\n")

    collectors = [
        ("github", collect_github, "github.json"),
        ("youtube", collect_youtube, "youtube.json"),
        ("reddit", collect_reddit, "reddit.json"),
        ("hn", collect_hn, "hn.json"),
    ]

    all_validations = []

    for source_name, collect_fn, filename in collectors:
        print(f"\n{'─'*40}")
        try:
            data = collect_fn()
            save_json(data, filename)
            validation = validate(source_name, data.get("items", []))
            all_validations.append(validation)
        except Exception as e:
            print(f"  [ERROR] {source_name} 수집 실패: {e}")
            all_validations.append({
                "source": source_name,
                "total": 0,
                "duplicate_url_ratio": 0.0,
                "freshness_7d_ratio": 0.0,
                "empty_title_ratio": 0.0,
                "empty_url_ratio": 0.0,
                "keyword_relevance_ratio": 0.0,
                "issues": [f"수집 실패: {e}"],
            })

    # summary.json 저장
    summary = {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "validations": all_validations,
        "total_collected": sum(v["total"] for v in all_validations),
    }
    save_json(summary, "summary.json")

    # 터미널 리포트
    print_report(all_validations)


if __name__ == "__main__":
    main()
