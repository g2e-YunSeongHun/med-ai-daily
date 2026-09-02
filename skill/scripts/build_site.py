#!/usr/bin/env python3
"""누적 기사 JSON으로 docs/index.html(뉴스 피드)을 생성한다.

Usage:
  python build_site.py <articles_json> <output_html> [--days 30]

- 최근 N일(기본 30일, KST 오늘 포함) 기사만 렌더링한다.
- 날짜별 구분선 아래 기사 행이 이어지는 뉴스 피드. 가장 최근 `수집일` 기사에는 NEW 표시.
- 기사 객체 필드: 섹션, 제목, 기관매체, 관련기관, 활용분야, 구분, 날짜, 링크, 기사요약,
  세부분석(화면에는 표시하지 않음), 이미지(선택), 수집일
"""

from __future__ import annotations

import argparse
import html
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE = SCRIPT_DIR.parent / "templates" / "dashboard.html"
KST = timezone(timedelta(hours=9))
WEEKDAYS = "월화수목금토일"
CATS = {"연구", "도입", "정책", "트렌드"}


def esc(v) -> str:
    return html.escape(str(v or "").strip())


def fmt_long(d: date) -> str:
    return f"{d.year}년 {d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"


def cat_of(a: dict) -> str:
    c = str(a.get("구분", "")).strip()
    return c if c in CATS else "트렌드"


def search_text(a: dict) -> str:
    parts = [a.get(k, "") for k in ("제목", "기관매체", "관련기관", "활용분야", "기사요약")]
    return esc(" ".join(str(p) for p in parts if p).lower())


def item_html(a: dict, is_new: bool) -> str:
    sec = a.get("섹션", "")
    cat = cat_of(a)
    url = str(a.get("링크", "")).strip()
    href = html.escape(url, quote=True) if url else "#"
    img = str(a.get("이미지", "")).strip()
    thumb = (
        f'<img class="thumb" src="{html.escape(img, quote=True)}" alt="" loading="lazy" referrerpolicy="no-referrer" />'
        if img else ""
    )
    meta = [
        f'<span class="sec{" overseas" if sec == "해외" else ""}">{esc(sec)}</span>',
        f'<span class="tag tag-{cat}">{cat}</span>',
    ]
    if is_new:
        meta.insert(0, '<span class="new">NEW</span>')
    foot = " · ".join(esc(a[k]) for k in ("기관매체", "관련기관") if a.get(k))
    field = f'<span class="field">{esc(a["활용분야"])}</span>' if a.get("활용분야") else ""
    return (
        f'<article class="item{"" if img else " no-img"}" data-sec="{esc(sec)}" data-cat="{cat}" data-text="{search_text(a)}">'
        f'<div class="meta">{" ".join(meta)}</div>'
        f'<h3><a href="{href}" target="_blank" rel="noreferrer">{esc(a.get("제목", "제목 미상"))}</a></h3>'
        f'<p>{esc(a.get("기사요약") or "원문 미확보")}</p>'
        f'<div class="foot"><span>{foot}</span>{field}</div>'
        f"{thumb}</article>"
    )


def day_html(iso: str, n: int) -> str:
    try:
        d = date.fromisoformat(iso)
        label = f"{d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"
    except ValueError:
        label = esc(iso)
    return f'<div class="day"><h2>{label}</h2><span class="n">{n}건</span><span class="line"></span></div>'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("articles_json")
    ap.add_argument("output_html")
    ap.add_argument("--days", type=int, default=30)
    args = ap.parse_args()

    with open(args.articles_json, encoding="utf-8-sig") as fh:
        articles = json.load(fh)

    today = datetime.now(KST).date()
    start_iso = (today - timedelta(days=args.days - 1)).isoformat()
    recent = [a for a in articles if str(a.get("날짜", "")) >= start_iso]
    recent.sort(key=lambda a: (a.get("날짜", ""), a.get("기관매체", ""), a.get("제목", "")), reverse=True)

    latest_run = max((str(a.get("수집일", "")) for a in recent), default="")
    per_day: dict[str, int] = {}
    for a in recent:
        per_day[str(a.get("날짜", ""))] = per_day.get(str(a.get("날짜", "")), 0) + 1

    parts: list[str] = []
    cur = None
    new_count = 0
    for a in recent:
        d = str(a.get("날짜", ""))
        if d != cur:
            cur = d
            parts.append(day_html(d, per_day[d]))
        is_new = bool(latest_run) and str(a.get("수집일", "")) == latest_run
        new_count += is_new
        parts.append(item_html(a, is_new))
    feed = "\n".join(parts) if parts else '<div class="empty">아직 수집된 기사가 없습니다.</div>'

    out = TEMPLATE.read_text(encoding="utf-8")
    for k, v in {
        "{{갱신일}}": fmt_long(today),
        "{{총건수}}": str(len(recent)),
        "{{국내건수}}": str(sum(1 for a in recent if a.get("섹션") == "국내")),
        "{{해외건수}}": str(sum(1 for a in recent if a.get("섹션") == "해외")),
        "<!--FEED-->": feed,
    }.items():
        out = out.replace(k, v)

    out_path = Path(args.output_html)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")
    print(f"RENDERED total={len(recent)} new={new_count} window={start_iso}~{today.isoformat()}")


if __name__ == "__main__":
    main()
