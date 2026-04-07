# trend-collector

GitHub, YouTube, Reddit, Hacker News 에서 기술 트렌드 데이터를 매일 자동 수집하는 파이프라인.

[![Collect](https://github.com/<YOUR_GITHUB_USER>/<YOUR_REPO>/actions/workflows/collect.yml/badge.svg)](https://github.com/<YOUR_GITHUB_USER>/<YOUR_REPO>/actions/workflows/collect.yml)

## 데이터 소스

| 소스 | 수집 내용 |
|------|---------|
| GitHub | 주요 저장소 릴리즈 + GitHub Trending Top 30 |
| YouTube | AWS / Azure / Google Cloud / freeCodeCamp 채널 최신 영상 |
| Reddit | r/aws, r/AZURE, r/MachineLearning, r/LocalLLaMA, r/ClaudeAI, r/ChatGPT 인기글 |
| Hacker News | aws, claude, openai, azure, llm, anthropic 키워드 최신 스토리 |

## 출력 파일

```
data/
  github.json       — GitHub 수집 원본
  youtube.json      — YouTube 수집 원본
  reddit.json       — Reddit 수집 원본
  hn.json           — Hacker News 수집 원본
  latest.json       — 4개 소스 통합 (중복 제거, 최신 200건)
  last_updated.txt  — 마지막 수집 시각 (KST)
```

`latest.json` 아이템 스키마:
```json
{
  "source": "github|youtube|reddit|hn",
  "title": "...",
  "url": "...",
  "published_at": "2024-01-01T00:00:00Z",
  "score": 0,
  "summary_ko": null
}
```

## 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 전체 수집기 실행
python collectors/run_all.py
```

## 자동 실행 (GitHub Actions)

`.github/workflows/collect.yml` 이 매일 **09:00 KST** (UTC 00:00) 에 자동 실행되어 `data/` 를 업데이트하고 커밋한다.

수동 실행: GitHub Actions 탭 → **Collect Trend Data** → **Run workflow**
