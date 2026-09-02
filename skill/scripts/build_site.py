#!/usr/bin/env python3
"""누적 기사 + 요약 JSON으로 docs/index.html을 생성한다.

Usage:
  python build_site.py <articles_json> <summary_json> <output_html> [--days 30]

- articles_json: append_articles.py가 관리하는 누적 기사 배열
- summary_json: {"핵심동향": [...], "주목할기관/기업": [...], "시사점": "..."} (최근 7일 기준)
- 최근 N일(기본 30일, KST 오늘 포함) 기사만 렌더링한다.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RENDERER = SCRIPT_DIR / "render_dashboard.py"
TEMPLATE = SCRIPT_DIR.parent / "templates" / "dashboard.html"
KST = timezone(timedelta(hours=9))
WEEKDAYS = "월화수목금토일"


def _load(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _fmt(d) -> str:
    return f"{d.year}년 {d.month}월 {d.day}일({WEEKDAYS[d.weekday()]})"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("articles_json")
    parser.add_argument("summary_json")
    parser.add_argument("output_html")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()

    articles = _load(Path(args.articles_json), [])
    summary = _load(Path(args.summary_json), {})
    output = Path(args.output_html)

    today = datetime.now(KST).date()
    start = today - timedelta(days=args.days - 1)
    start_iso = start.isoformat()

    recent = [a for a in articles if str(a.get("날짜", "")) >= start_iso]
    payload = {
        "시작일": _fmt(start),
        "종료일": _fmt(today),
        "생성일": _fmt(today),
        "국내기사": [a for a in recent if a.get("섹션") == "국내"],
        "해외기사": [a for a in recent if a.get("섹션") == "해외"],
        "주간요약": summary,
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(payload, tmp, ensure_ascii=False)
        tmp_path = tmp.name

    subprocess.run(
        [sys.executable, str(RENDERER), tmp_path, str(output), str(TEMPLATE)],
        check=True,
    )
    Path(tmp_path).unlink(missing_ok=True)
    print(
        f"RENDERED domestic={len(payload['국내기사'])} overseas={len(payload['해외기사'])} "
        f"window={start_iso}~{today.isoformat()}"
    )


if __name__ == "__main__":
    main()
