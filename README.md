# med-ai-daily

의료 AI · 응급의료 AI 일간 뉴스 피드. 매일 새벽 2시(KST) 클라우드 루틴이 전날 기사를 수집해 누적하고 피드 페이지를 재생성한다.

- 피드: https://g2e-yunseonghun.github.io/med-ai-daily/
- 수집·작성 절차: `skill/SKILL.md`
- 누적 데이터: `data/articles.json`
- 출력: `docs/index.html` (최근 30일만 표시, GitHub Pages가 서빙)

## 구조

```
skill/
  SKILL.md                    일간 수집 절차
  references/search-rules.md  검색 축·도메인·포함/제외 규칙
  scripts/extract.py          URL 본문·발행일·og:image 추출 (trafilatura → Playwright 폴백)
  scripts/append_articles.py  새 기사를 누적 파일에 URL 중복 대조 후 병합, 수집일 기록
  scripts/build_site.py       최근 30일 기사 → docs/index.html
  templates/dashboard.html    피드 템플릿 (필터·검색)
data/articles.json            누적 기사
docs/index.html               피드
```

## 수동 실행

```bash
pip install trafilatura playwright && playwright install chromium
python skill/scripts/append_articles.py _work/new_articles.json data/articles.json
python skill/scripts/build_site.py data/articles.json docs/index.html
```
