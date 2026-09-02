#!/usr/bin/env python3
"""누적 기사 JSON으로 docs/index.html을 생성한다.

Usage:
  python build_site.py <articles_json> <output_html> [--days 30]

- 최근 N일(기본 30일, KST 오늘 포함) 기사만 렌더링한다.
- "신규" 섹션 = 가장 최근 `수집일` 값을 가진 기사. 나머지는 접힌 리스트.
- 기사 객체 필드: 섹션, 제목, 기관매체, 관련기관, 활용분야, 구분, 날짜, 링크, 기사요약,
  세부분석{관련 기업/기관, 기술/제품, 핵심 수치}, 이미지(선택), 수집일
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
DETAIL_KEYS = ("관련 기업/기관", "기술/제품", "핵심 수치")


def esc(v) -> str:
    return html.escape(str(v or "").strip())


def fmt_long(d: date) -> str:
    return f"{d.year}년 {d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"


def fmt_short(iso: str) -> str:
    try:
        d = date.fromisoformat(iso)
        return f"{d.month:02d}-{d.day:02d} {WEEKDAYS[d.weekday()]}"
    except ValueError:
        return esc(iso)


def cat_of(a: dict) -> str:
    c = str(a.get("구분", "")).strip()
    return c if c in CATS else "트렌드"


def search_text(a: dict) -> str:
    parts = [a.get(k, "") for k in ("제목", "기관매체", "관련기관", "활용분야", "기사요약")]
    return esc(" ".join(str(p) for p in parts if p).lower())


def meta_html(a: dict, with_source: bool = True) -> str:
    sec = a.get("섹션", "")
    sec_cls = "sec overseas" if sec == "해외" else "sec"
    cat = cat_of(a)
    bits = [f'<span class="{sec_cls}">{esc(sec)}</span>', f'<span class="tag tag-{cat}">{cat}</span>']
    if a.get("활용분야"):
        bits.append(f'<span class="tag tag-field">{esc(a["활용분야"])}</span>')
    if with_source:
        src = " · ".join(esc(a[k]) for k in ("기관매체", "관련기관") if a.get(k))
        if src:
            bits.append(f"<span>· {src}</span>")
    return f'<div class="meta">{" ".join(bits)}</div>'


def detail_html(a: dict) -> str:
    d = a.get("세부분석") or {}
    rows = [(k, d.get(k)) for k in DETAIL_KEYS if isinstance(d.get(k), str) and d.get(k).strip()]
    if not rows:
        return ""
    inner = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in rows)
    return f'<dl class="detail">{inner}</dl>'


def link_html(a: dict) -> str:
    url = str(a.get("링크", "")).strip()
    return f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noreferrer">원문 보기</a>' if url else ""


def card_html(a: dict) -> str:
    img = str(a.get("이미지", "")).strip()
    thumb = (
        f'<img class="thumb" src="{html.escape(img, quote=True)}" alt="" loading="lazy" referrerpolicy="no-referrer" />'
        if img else ""
    )
    return (
        f'<article class="card" data-sec="{esc(a.get("섹션"))}" data-cat="{cat_of(a)}" data-text="{search_text(a)}">'
        f'<div class="body">{meta_html(a)}'
        f'<h3 class="serif">{esc(a.get("제목", "제목 미상"))}</h3>'
        f'<p>{esc(a.get("기사요약") or "원문 미확보")}</p>'
        f'{detail_html(a)}'
        f'<div class="links">{link_html(a)}<span class="count">{fmt_short(a.get("날짜", ""))}</span></div>'
        f"</div>{thumb}</article>"
    )


def row_html(a: dict) -> str:
    sec = a.get("섹션", "")
    cat = cat_of(a)
    return (
        f'<details class="row" data-sec="{esc(sec)}" data-cat="{cat}" data-text="{search_text(a)}">'
        f"<summary>"
        f'<span class="d">{fmt_short(a.get("날짜", ""))}</span>'
        f'<span class="s{" overseas" if sec == "해외" else ""}">{esc(sec)}</span>'
        f'<span class="t tag-{cat}">{cat}</span>'
        f'<span class="title">{esc(a.get("제목", "제목 미상"))}</span>'
        f'<span class="src">{esc(a.get("기관매체", ""))}</span>'
        f"</summary>"
        f'<div class="open">{meta_html(a)}<div>{esc(a.get("기사요약") or "원문 미확보")}</div>{detail_html(a)}<div class="links">{link_html(a)}</div></div>'
        f"</details>"
    )


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
    new = [a for a in recent if latest_run and str(a.get("수집일", "")) == latest_run]
    old = [a for a in recent if a not in new]

    if new:
        new_dates = sorted({str(a.get("날짜", "")) for a in new}, reverse=True)
        new_title = fmt_long(date.fromisoformat(new_dates[0])) if len(new_dates) == 1 else f"{fmt_short(new_dates[-1])} ~ {fmt_short(new_dates[0])}"
        n_dom = sum(1 for a in new if a.get("섹션") == "국내")
        new_summary = f"국내 {n_dom} · 해외 {len(new) - n_dom}"
        new_cards = "\n".join(card_html(a) for a in new)
    else:
        new_title, new_summary = "새 기사 없음", ""
        new_cards = '<div class="empty">최근 수집에서 추가된 기사가 없습니다.</div>'

    rows = "\n".join(row_html(a) for a in old) if old else '<div class="empty">이전 기사가 없습니다.</div>'

    tpl = TEMPLATE.read_text(encoding="utf-8")
    out = tpl
    for k, v in {
        "{{갱신일}}": fmt_long(today),
        "{{총건수}}": str(len(recent)),
        "{{국내건수}}": str(sum(1 for a in recent if a.get("섹션") == "국내")),
        "{{해외건수}}": str(sum(1 for a in recent if a.get("섹션") == "해외")),
        "{{신규날짜}}": new_title,
        "{{신규건수요약}}": new_summary,
        "{{이전건수}}": str(len(old)),
        "<!--NEW_CARDS-->": new_cards,
        "<!--ARCHIVE_ROWS-->": rows,
    }.items():
        out = out.replace(k, v)

    out_path = Path(args.output_html)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")
    print(f"RENDERED total={len(recent)} new={len(new)} old={len(old)} window={start_iso}~{today.isoformat()}")


if __name__ == "__main__":
    main()
