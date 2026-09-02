---
name: med-ai-daily
description: '의료·응급의료 AI 일간 뉴스 피드. 어제(KST) 발행된 국내/해외 기사를 검색해 원문·발행일을 검증하고, 누적 데이터에 병합한 뒤 기사별 요약을 작성해 docs/index.html 피드를 재생성한다.'
---

# 의료·응급의료 AI 일간 뉴스 피드

매일 1회 실행된다. 어제 하루 발행된 의료 AI · 응급의료 AI **기사**를 수집해 누적하고, 피드형 HTML을 다시 만든다. 학술 논문은 수집하지 않는다.

**IMPORTANT: 모든 출력은 한국어로 작성한다.**

## Quick Start

1. 대상 날짜 = KST 기준 어제.
2. 국내 기사, 해외 기사를 검색해 후보 URL을 모은다.
3. `scripts/extract.py`로 원문과 발행일을 검증한다.
4. 누적 `data/articles.json`과 대조해 중복·재보도를 제거한다.
5. 새 기사마다 요약과 세부분석을 작성한다.
6. `scripts/append_articles.py`로 누적 파일에 병합한다.
7. `scripts/build_site.py`로 `docs/index.html`을 재생성한다.

## 저장소 구조

```
skill/
  SKILL.md                    이 문서
  references/search-rules.md  검색 축·도메인·포함/제외 규칙
  scripts/extract.py          URL → 본문·발행일·og:image 추출 (trafilatura → Playwright 폴백)
  scripts/append_articles.py  새 기사를 누적 파일에 URL 중복 대조 후 병합, 수집일 기록
  scripts/build_site.py       최근 30일 기사 → docs/index.html (날짜별 뉴스 피드)
  templates/dashboard.html    피드 템플릿 (필터·검색 JS 포함)
data/articles.json            누적 기사 (전체 보관)
docs/index.html               피드 (GitHub Pages)
_work/                        작업 파일. git에 올리지 않는다
```

모든 명령은 **저장소 루트**에서 실행한다.

## Environment

```bash
pip install trafilatura playwright
playwright install chromium   # 실패해도 계속 진행한다. trafilatura만으로 동작한다
```

## Workflow

### Step 1. 대상 날짜 계산

KST 기준 어제 하루가 대상이다. 서버 시간대에 의존하지 말고 명시적으로 계산한다.

```bash
TARGET=$(TZ=Asia/Seoul date -d yesterday +%F)
```

이 값을 `TARGET`이라 부른다. 기간을 늘리지 않는다. 기사가 적은 날은 적게 싣는다.

### Step 2. 검색

`references/search-rules.md`의 검색 축과 도메인 우선순위를 따른다. 두 카테고리를 모두 수행한다.

- **국내 기사**: 8개 축. `TARGET` 날짜와 함께 검색하고, `0건`으로 결론 내기 전에 국내 필수 도메인 site-pass를 반드시 수행한다.
- **해외 기사**: 5개 축. 뉴스 매체·업계 매체 기사만. 학술 논문(PubMed, 저널 사이트)은 제외한다.

공통 규칙:

- 노이즈 도메인 제외: `youtube.com`, `blog.naver.com`, `tistory.com`, `brunch.co.kr`, `medium.com`, `velog.io`, `reddit.com`
- 검색 결과와 포털 뉴스는 후보 시드일 뿐이다. 포함 여부는 원문 URL을 열어 판단한다.
- `Agent` 툴이 있으면 두 카테고리를 병렬로 돌려도 된다. 없으면 순차 수행한다.

### Step 3. 원문·발행일 검증

후보 URL 전체를 한 번에 넘긴다.

```bash
echo '["https://url1", "https://url2"]' | python skill/scripts/extract.py > _work/extracted.json
```

반환: `[{"url","text","date","title","image","success"}]` (`image`는 og:image URL, 없으면 빈 문자열)

판정 규칙:

- `success=true` 이고 `date == TARGET` → 포함
- `success=true` 이고 `date=null` → 검색 스니펫·URL 경로에서 날짜를 재확인. `TARGET`이면 포함
- `success=false`여도 날짜가 `TARGET`으로 확정되면 포함. `원문`은 빈 문자열
- 날짜를 확정할 수 없거나 `TARGET`이 아니면 제외

시차 주의: 해외 기사는 현지 날짜 기준으로 `TARGET`이면 포함한다. 하루 차이로 KST 기준 오늘 날짜가 붙은 해외 기사도 포함해도 된다. 단 다음 실행에서 URL 중복으로 자동 제외되므로 걱정하지 않는다.

### Step 4. 누적 데이터와 중복 대조

`data/articles.json`을 읽고 아래를 걸러낸다.

- 동일 URL (`append_articles.py`가 자동 처리하지만, 여기서도 미리 제외한다)
- **URL이 다르더라도 같은 제품/사업/연구 발표의 재보도**. 제목·관련기관·기술/제품이 겹치면 최근 14일 누적 기사와 비교해 판단한다
- 이번 회차 안에서 같은 내용을 여러 매체가 보도한 경우 대표 1건만 남긴다 (`search-rules.md` 동률 해소 규칙)
- 의료·응급의료 직접 관련성이 낮은 기사

### Step 5. 기사별 분석 작성

남은 기사마다 아래 객체를 만들어 `_work/new_articles.json`에 배열로 저장한다.

```json
{
  "섹션": "국내",
  "제목": "기사 제목 (해외는 한국어 번역)",
  "기관매체": "매체명 또는 저널명",
  "관련기관": "기사에 등장하는 병원/기업/기관",
  "활용분야": "트리아지, 영상판독 등",
  "구분": "연구|도입|정책|트렌드",
  "날짜": "YYYY-MM-DD",
  "링크": "원문 URL",
  "이미지": "extract.py가 돌려준 image URL. 없으면 생략",
  "기사요약": "3~5문장. 누가, 무엇을, 왜, 어떻게.",
  "세부분석": {
    "관련 기업/기관": "...",
    "기술/제품": "...",
    "핵심 수치": "..."
  }
}
```

- `섹션`은 `국내` 또는 `해외`.
- **`원문`에 있는 내용만 근거로 삼는다. 추측하지 않는다.** 원문에 없는 수치·기관명·날짜를 지어내지 않는다.
- 원문이 비어 있으면 `기사요약`은 `원문 미확보`, `세부분석` 값은 빈 문자열.
- 해외 기사 제목·요약은 의미 보존을 우선해 한국어로 쓴다.

병합:

```bash
python skill/scripts/append_articles.py _work/new_articles.json data/articles.json
```

마지막 줄 `ADDED:<n> SKIPPED:<m> TOTAL:<t>`를 확인한다. `ADDED:0`이면 Step 7로 건너뛴다.

### Step 6. 피드 재생성

```bash
python skill/scripts/build_site.py data/articles.json docs/index.html
```

- 최근 30일 기사만 렌더링된다. 그 이전 기사는 `data/articles.json`에만 남는다.
- 날짜별 구분선 아래 기사 행이 이어지는 뉴스 피드 형태다. 가장 최근 `수집일`의 기사에는 NEW 표시가 붙는다.
- `세부분석`은 화면에 표시하지 않지만 데이터에는 남기므로 계속 작성한다.

### Step 7. 커밋

- `ADDED`가 1 이상이면 `data/`와 `docs/`를 커밋한다. `_work/`는 커밋하지 않는다.
- 커밋 메시지: `brief: {TARGET} 국내 {n}건 해외 {m}건`
- `ADDED:0`이면 **커밋하지 않는다**. 빈 커밋을 만들지 않는다.

## Error Handling

- 검색 결과 0건인 쿼리는 건너뛴다.
- `playwright install`이 실패해도 `extract.py`는 trafilatura만으로 동작한다. 계속 진행한다.
- `extract.py`가 원문 추출에 실패해도 날짜가 확정되면 포함한다.
- 그날 기사가 정말 없으면 커밋 없이 종료하고 그 사실을 보고한다.

## Quality Bar

- 요약에는 누가, 무엇을, 왜, 어떻게가 들어간다.
- 세부 분석은 원문에 없는 수치를 지어내지 않는다.
- 와일드카드 검색 결과는 의료·응급의료 직접 관련성을 다시 검토한다.
- 국내·해외 균형을 억지로 맞추지 않는다.
