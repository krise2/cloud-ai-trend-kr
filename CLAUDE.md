# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cloud/AI 트렌드 자동 수집·요약 사이트. GitHub Actions가 매일 08:00/20:00 KST에 4개 소스에서 데이터를 수집해 Supabase DB에 적재하고, Claude Code 세션(수동)에서 에이전트 토론으로 분석 후 Next.js 웹사이트에 표시한다.

## Repository Structure

```
trend/
├── collectors/          Python 수집기 (GitHub Trending, YouTube RSS, Reddit, HN)
│   └── run_all.py       4개 수집기 실행 + Supabase INSERT
├── agents/
│   └── analyze.py       Supabase DB 조회·업데이트·latest.json 저장 유틸
├── data/                로컬 전용 (gitignore), 분석 결과만 저장
│   ├── latest.json      분석 완료 아이템 누적 (collected_at 포함)
│   └── last_updated.txt 마지막 수집 시각 (KST ISO8601)
├── web/                 Next.js 16 App Router 프론트엔드
│   └── src/
│       ├── app/page.tsx          서버 컴포넌트 — getData() 호출
│       ├── lib/data.ts           fs.readFileSync로 data/latest.json 읽기
│       ├── lib/utils.ts          categorize() — 클라이언트 안전
│       └── components/
│           ├── NewsDashboard.tsx 사이드바 필터 상태 관리 (client)
│           ├── TrendFeed.tsx     TOP3 + 피드 렌더링 (client)
│           ├── TrendItem.tsx     개별 아이템 행 (client)
│           └── SourceLogos.tsx   인라인 SVG 브랜드 로고
└── .github/workflows/collect.yml  자동 수집 워크플로우 (08:00/20:00 KST)
```

## Data Pipeline

```
[자동] GitHub Actions (08:00 KST = UTC 23:00 전날, 20:00 KST = UTC 11:00)
  → collectors/run_all.py 실행
  → Supabase collection_runs + trend_items 테이블에 raw INSERT
  → git push 없음

[수동] Claude Code 세션 — "분석해줘" 트리거
  → Supabase DB에서 미분석 항목(summary_ko IS NULL) 조회
  → Heavy Weight 에이전트 토론으로 Top 20 선정
  → DB UPDATE (summary_ko, project_relevant, relevance_score, project_note)
  → data/latest.json 누적 저장 (모든 회차, URL 중복 제거)
```

## Supabase

- Project URL: `https://dlrcpzrgflsmizgdcyeo.supabase.co`
- 키는 `.env` 파일에 저장 (gitignore)
- 테이블: `collection_runs`, `trend_items`
- 미분석 조회 쿼리: `summary_ko IS NULL`

## "분석해줘" 트리거 — 실행 절차

사용자가 **"분석해줘"** 라고 하면 아래 절차를 **반드시** 따른다.

### Step 1: 미분석 항목 조회
```python
python3 -c "
import urllib.request, json
url = 'https://dlrcpzrgflsmizgdcyeo.supabase.co'
key = open('.env').read().split('SUPABASE_SERVICE_KEY=')[1].strip()
headers = {'apikey': key, 'Authorization': 'Bearer ' + key}
req = urllib.request.Request(
    url + '/rest/v1/trend_items?summary_ko=is.null&order=score.desc&limit=200'
        + '&select=id,source,title,score',
    headers=headers)
items = json.loads(urllib.request.urlopen(req).read())
print(f'미분석: {len(items)}건')
for it in items[:20]:
    print(f'  [{it[\"id\"]:4d}][{it[\"source\"]:7s}] score={it[\"score\"]:6} | {it[\"title\"][:70]}')
"
```

### Step 2: Heavy Weight 에이전트 토론 (병렬)
Round 1 — 4개 에이전트 병렬 스폰:
- `analyst` → 소스별 정규화 점수, 중요도 산출
- `content-researcher` → 트렌드 맥락 평가, 핵심 주제 도출
- `customer-insights` → Agents 대시보드 프로젝트 관련성 평가 (relevance_score 0–5)
- `critic` → 선택 기준 도전, 빠진 관점 지적

Round 2 — `master` 충돌 정리 → Top 20 후보 + summary_ko 초안

Round 3 — `tyranno` 최종 승인 (최대 3개 교체 권고 가능)

### Step 3: DB 업데이트
Supabase REST API PATCH로 각 item_id에 분석 결과 기록:
- `summary_ko`: 한국어 요약 (80자 이내)
- `project_relevant`: true/false
- `relevance_score`: 0–5 (project_relevant=true 항목만)
- `project_note`: 적용 방안 설명 (한국어)

### Step 4: latest.json 저장
```python
python3 -c "
import urllib.request, json
from pathlib import Path
url = 'https://dlrcpzrgflsmizgdcyeo.supabase.co'
key = open('.env').read().split('SUPABASE_SERVICE_KEY=')[1].strip()
headers = {'apikey': key, 'Authorization': 'Bearer ' + key}
req = urllib.request.Request(
    url + '/rest/v1/trend_items?summary_ko=not.is.null'
        + '&select=source,title,url,published_at,score,summary_ko,project_relevant,relevance_score,project_note,collected_at'
        + '&order=collected_at.desc,score.desc',
    headers=headers)
all_items = json.loads(urllib.request.urlopen(req).read())
seen = set()
items = [it for it in all_items if it.get('url') and not seen.add(it['url']) and it['url'] not in seen]
req2 = urllib.request.Request(url + '/rest/v1/collection_runs?order=collected_at.desc&limit=1&select=collected_at', headers=headers)
ca = json.loads(urllib.request.urlopen(req2).read())[0]['collected_at']
Path('data').mkdir(exist_ok=True)
Path('data/latest.json').write_text(json.dumps(items, ensure_ascii=False, indent=2))
Path('data/last_updated.txt').write_text(ca + '\n')
print(f'저장 완료: {len(items)}건')
"
```

## TrendItem Schema

```json
{
  "source": "github | youtube | reddit | hn",
  "title": "string",
  "url": "string",
  "published_at": "2024-01-01T00:00:00Z",
  "collected_at": "2024-01-01T00:00:00Z",
  "score": 0,
  "summary_ko": "한국어 요약 (80자 이내) | null",
  "project_relevant": true,
  "relevance_score": 3.5,
  "project_note": "적용 방안 설명"
}
```

`project_relevant: true` 항목은 `/insights` 페이지에 별도 표시됨.

## Running Locally

```bash
# 웹 개발 서버 — 포트 3001 고정 (3000은 Agents 대시보드)
cd web && npm run dev -- --port 3001
```

## 에이전트 분석 프로토콜 (필수)

데이터 분석 시 **무조건 Heavy Weight 토론**을 사용한다. 이는 선택이 아닌 필수 규칙이다.

### Heavy Weight 분석 절차

```
[Round 1 — 병렬 의견 수집]
  analyst         → 데이터 수치 분석, 중요도 점수 산출
  content-researcher → 트렌드 맥락 및 관련성 평가
  security-auditor → 보안/리스크 관련 항목 식별
  customer-insights → 사용자 가치 및 적용 가능성 판단
  critic          → 선택 기준 도전 ("왜 이게 중요?", "빠진 항목은?")
    ↓
[Round 2 — master 충돌 정리]
  이견 표면화 및 선별 기준 최종 정렬
    ↓
[Round 3 — tyranno 최종 확정]
  top 20 확정, relevance_score 검증
```

### 분석 출력 스키마 (project_relevant=true 항목)
```json
{
  "project_relevant": true,
  "relevance_score": 3.5,   // 0–5, 0.5 단위 — Agents 대시보드 적용 적합도
  "project_note": "멀티 에이전트 오케스트레이션 설계에 적용 가능. Tyranno 시스템의 분산 실행 패턴 참고용."
}
```

### relevance_score 기준 (Agents 대시보드 프로젝트 기준)
- 5.0: 즉시 적용 가능한 기술/패턴
- 4.0–4.5: 아키텍처 결정에 직접 영향
- 3.0–3.5: 중기 로드맵에 참고할 인사이트
- 2.0–2.5: 간접 참고용 (배경 지식)
- 1.0–1.5: 모니터링 필요 (아직 성숙하지 않음)

## Design System

`web/src/app/globals.css` + `web/tailwind.config.ts`에 다크 대시보드 디자인 토큰이 정의됨.
핵심 클래스: `card-base`, `kpi-card`, `report-row`, `section-title`, `nav-item`, `badge-*`
색상 기조: 배경 `#0d1117`, 텍스트 `#f1f5f9`, 포인트 amber(`#f59e0b`)
