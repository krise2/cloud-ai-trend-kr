#!/usr/bin/env python3
"""
agents/analyze.py — DB에서 미분석 항목을 읽고, 분석 결과를 DB에 업데이트한다.

사용법:
  python agents/analyze.py            # 미분석 항목 조회 + 출력
  python agents/analyze.py --save     # 최신 분석 완료 항목 → data/latest.json 저장
"""

from __future__ import annotations
import os
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def _load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def _get_client():
    _load_env()
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("[ERROR] .env에 SUPABASE_URL, SUPABASE_SERVICE_KEY 필요")
        sys.exit(1)
    return create_client(url, key)


# ── 조회 ─────────────────────────────────────────────────────

def fetch_unanalyzed(limit_runs: int = 10) -> list[dict]:
    """최근 N회차 중 미분석 항목(summary_ko IS NULL)을 반환."""
    db = _get_client()

    runs = (
        db.table("collection_runs")
        .select("id, collected_at, total_items")
        .order("collected_at", desc=True)
        .limit(limit_runs)
        .execute()
    )

    results = []
    for run in runs.data:
        items = (
            db.table("trend_items")
            .select("id, source, title, url, score, summary_ko, published_at")
            .eq("run_id", run["id"])
            .is_("summary_ko", "null")
            .order("score", desc=True)
            .execute()
        )
        if items.data:
            results.append({
                "run_id": run["id"],
                "collected_at": run["collected_at"],
                "unanalyzed_count": len(items.data),
                "items": items.data,
            })
    return results


def fetch_run_items(run_id: int) -> list[dict]:
    """특정 회차의 전체 항목 반환 (분석 여부 무관)."""
    db = _get_client()
    items = (
        db.table("trend_items")
        .select("id, source, title, url, score, summary_ko, published_at")
        .eq("run_id", run_id)
        .order("score", desc=True)
        .execute()
    )
    return items.data


# ── 업데이트 ──────────────────────────────────────────────────

def update_item(
    item_id: int,
    summary_ko: str,
    project_relevant: bool = False,
    relevance_score: float | None = None,
    project_note: str | None = None,
):
    """단일 아이템에 분석 결과를 기록한다."""
    db = _get_client()
    data: dict = {"summary_ko": summary_ko, "project_relevant": project_relevant}
    if relevance_score is not None:
        data["relevance_score"] = relevance_score
    if project_note:
        data["project_note"] = project_note
    db.table("trend_items").update(data).eq("id", item_id).execute()


def batch_update(updates: list[dict]):
    """
    여러 아이템을 한 번에 업데이트한다.

    updates 형식:
    [
      {
        "id": 1,
        "summary_ko": "한국어 요약",
        "project_relevant": True,
        "relevance_score": 4.0,
        "project_note": "적용 방안 설명"
      },
      ...
    ]
    """
    db = _get_client()
    for u in updates:
        item_id = u.pop("id")
        db.table("trend_items").update(u).eq("id", item_id).execute()
    print(f"  [batch_update] {len(updates)}건 완료")


# ── latest.json 저장 ──────────────────────────────────────────

def save_latest_json():
    """
    분석 완료된 모든 회차의 항목을 누적해 data/latest.json으로 저장한다.
    URL 기준 중복 제거 (최신 회차 우선). collected_at 포함.
    """
    db = _get_client()

    # 전체 분석 완료 항목 (최신 수집순, score 내림차순)
    all_items = (
        db.table("trend_items")
        .select("source, title, url, published_at, score, summary_ko, "
                "project_relevant, relevance_score, project_note, collected_at")
        .not_.is_("summary_ko", "null")
        .order("collected_at", desc=True)
        .order("score", desc=True)
        .execute()
    )

    # URL 중복 제거 (최신 회차 우선)
    seen: set[str] = set()
    items = []
    for it in all_items.data:
        u = it.get("url", "")
        if u and u in seen:
            continue
        seen.add(u)
        items.append(it)

    # 최신 수집 시각
    run = (
        db.table("collection_runs")
        .select("collected_at")
        .order("collected_at", desc=True)
        .limit(1)
        .single()
        .execute()
    )
    collected_at = run.data["collected_at"]

    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "latest.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DATA_DIR / "last_updated.txt").write_text(collected_at + "\n", encoding="utf-8")
    print(f"  [save] latest.json 저장 완료: {len(items)}건 (누적, URL 중복 제거)")


# ── 진입점 ────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--save" in sys.argv:
        save_latest_json()
        sys.exit(0)

    unanalyzed = fetch_unanalyzed()

    if not unanalyzed:
        print("✓ 미분석 항목 없음. 모두 분석 완료.")
        sys.exit(0)

    total = sum(r["unanalyzed_count"] for r in unanalyzed)
    print(f"\n미분석 회차: {len(unanalyzed)}개  /  총 {total}건\n")

    for run in unanalyzed:
        print(f"  [run_id={run['run_id']}] {run['collected_at'][:16]}  —  {run['unanalyzed_count']}건")
        for item in run["items"][:5]:
            print(f"    [{item['source']:7s}] score={item['score']:5}  {item['title'][:70]}")
        if run["unanalyzed_count"] > 5:
            print(f"    ... 외 {run['unanalyzed_count'] - 5}건")
        print()

    print("→ Claude Code 세션에서 '분석해줘' 라고 하면 진행합니다.")
