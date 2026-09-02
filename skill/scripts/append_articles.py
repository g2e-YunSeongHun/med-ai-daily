#!/usr/bin/env python3
"""새 기사를 누적 articles.json에 병합한다.

Usage:
  python append_articles.py <new_articles_json> <articles_json_path>

<new_articles_json>: 기사 객체 배열. 각 객체는 최소 "섹션"("국내"|"해외"), "제목", "링크", "날짜"를 가진다.
<articles_json_path>: 누적 파일. 없으면 빈 배열로 시작한다.

URL(쿼리스트링·fragment·trailing slash 제거, 소문자)이 같은 기사는 건너뛴다.
stdout 마지막 줄에 "ADDED:<n> SKIPPED:<m> TOTAL:<t>"를 출력한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return data if isinstance(data, list) else []


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python append_articles.py <new_articles_json> <articles_json_path>")
        sys.exit(1)

    new_path = Path(sys.argv[1])
    store_path = Path(sys.argv[2])

    new_articles = _load(new_path)
    existing = _load(store_path)
    seen = {normalize_url(a.get("링크", "")) for a in existing if a.get("링크")}

    added = skipped = 0
    for article in new_articles:
        link = article.get("링크", "")
        key = normalize_url(link) if link else ""
        if not key or key in seen:
            skipped += 1
            continue
        if article.get("섹션") not in ("국내", "해외"):
            raise SystemExit(f"섹션 값이 잘못됨: {article.get('섹션')!r} ({link})")
        article.pop("원문", None)
        existing.append(article)
        seen.add(key)
        added += 1

    existing.sort(key=lambda a: (a.get("날짜", ""), a.get("기관매체", ""), a.get("제목", "")), reverse=True)

    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ADDED:{added} SKIPPED:{skipped} TOTAL:{len(existing)}")


if __name__ == "__main__":
    main()
