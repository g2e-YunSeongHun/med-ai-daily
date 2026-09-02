# med-ai-daily

의료 AI · 응급의료 AI 일간 뉴스 브리핑. 매일 오전 9시(KST) 클라우드 루틴이 전날 기사를 수집해 누적하고 대시보드를 재생성한다.

- 대시보드: https://g2e-yunseonghun.github.io/med-ai-daily/
- 수집·작성 절차: `skill/SKILL.md`
- 누적 데이터: `data/articles.json` (전체 기사), `data/summary.json` (최근 7일 요약)
- 출력: `docs/index.html` (최근 30일만 표시, GitHub Pages가 서빙)

## 구조

```
skill/
  SKILL.md                    일간 수집 절차
  references/search-rules.md  검색 축·도메인·포함/제외 규칙
  scripts/extract.py          URL 본문·발행일 추출 (trafilatura → Playwright 폴백)
  scripts/append_articles.py  새 기사를 누적 파일에 URL 중복 대조 후 병합
  scripts/build_site.py       최근 30일 기사 + 요약 → docs/index.html
  scripts/render_dashboard.py JSON → HTML 렌더러 (build_site.py가 호출)
  templates/dashboard.html    대시보드 템플릿
data/articles.json            누적 기사
data/summary.json             최근 7일 요약
docs/index.html               대시보드
```

## 수동 실행

```bash
pip install trafilatura playwright && playwright install chromium
python skill/scripts/append_articles.py _work/new_articles.json data/articles.json
python skill/scripts/build_site.py data/articles.json data/summary.json docs/index.html
```
