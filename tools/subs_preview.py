"""[자막 담당 도구] 렌더 전에, IT Reelsmaker 키트가 자막을 어떻게 끊을지 미리 보여 준다.

키트(Subtitles.tsx buildChunks)와 같은 규칙으로 captions.json 을 덩어리로 나눈다:
  · 구 경계 = 컷 이음새, 0.25초 이상 쉼, 문장 끝(. ! ? …)
  · 모드별 한 덩어리 최대: accent 3어절/20자 · plate 4어절/26자 · typewriter 10어절/52자 · gratitude 한 줄(약 13자)
  · 넘치면 가장 긴 쉼이나 쉼표 근처, 가운데에 가까운 곳에서 둘로 나눈다

    python3 tools/subs_preview.py edit/<id> [--mode plate|accent|typewriter|all]

한 줄 글자 수는 폰트 크기와 화면 폭(880px)으로 어림한다 (한글 1자 ≈ 글자 크기 px).
⚠ 표시: 3줄 이상으로 넘칠 덩어리, 한 어절만 남은 덩어리, 0.7초 미만으로 스치는 덩어리.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAUSE = 0.25
SENTENCE_END = re.compile(r"[.!?…][\"»”)]*$")
# gratitude: 감사일기 자막 (tools/gratitude.py) — 문장 단위, 한 줄(842px, 78px → 띄어쓰기 포함 약 13자)에 안 들어가면 한 줄씩 나눔
MODES = {"accent": (3, 20, 66), "plate": (4, 26, 60), "typewriter": (10, 52, 56), "gratitude": (40, 13, 78)}
MAX_W = 880 - 44


def wlen(ws) -> int:
    return sum(len(w["text"]) + 1 for w in ws)


def best_split(ws) -> int:
    best, best_score = 1, None
    for k in range(1, len(ws)):
        a, b = ws[:k], ws[k:]
        gap = min(PAUSE, max(0.0, ws[k]["start"] - ws[k - 1]["end"]))
        strong = 0.6 if re.search(r"[;:—–]$", ws[k - 1]["text"]) else 0.3 if ws[k - 1]["text"].endswith(",") else 0
        no_break = 1 if re.fullmatch(r"\d+[\d.,]*", ws[k - 1]["text"]) else 0
        score = (no_break, 1 if len(a) == 1 or len(b) == 1 else 0,
                 abs(wlen(a) - wlen(b)) / wlen(ws) - 2 * gap - strong)
        if best_score is None or score < best_score:
            best, best_score = k, score
    return best


def chunks(words, max_words, max_chars):
    fits = lambda ws: len(ws) <= max_words and wlen(ws) - 1 <= max_chars * 1.1  # noqa: E731
    phrases, cur = [], []
    for k, w in enumerate(words):
        prev = words[k - 1] if k else None
        if cur and prev and (w.get("seg") != prev.get("seg") or w["start"] - prev["end"] >= PAUSE
                             or w.get("speaker", "") != prev.get("speaker", "")):
            phrases.append(cur); cur = []
        cur.append(w)
        if SENTENCE_END.search(w["text"]):
            phrases.append(cur); cur = []
    if cur:
        phrases.append(cur)

    def split(ws):
        if len(ws) < 2 or fits(ws):
            return [ws]
        b = best_split(ws)
        return split(ws[:b]) + split(ws[b:])

    out = [ws for ph in phrases for ws in split(ph)]
    res = []
    for i, ws in enumerate(out):
        nxt = out[i + 1][0]["start"] if i + 1 < len(out) else None
        end = min(nxt, ws[-1]["end"] + 0.4) if nxt is not None else ws[-1]["end"] + 0.5
        res.append((ws[0]["start"], end, ws))
    return res


def lines_needed(text: str, size: int) -> int:
    per_line = max(1, MAX_W // size)
    return -(-len(text) // per_line)


def show(words, mode: str) -> int:
    mw, mc, size = MODES[mode]
    cs = chunks(words, mw, mc)
    warn = 0
    print(f"\n[{mode}] 덩어리 {len(cs)}개 (최대 {mw}어절/{mc}자, 글자 {size}px → 한 줄 약 {MAX_W // size}자)")
    for a, b, ws in cs:
        t = " ".join(w["text"] for w in ws)
        flags = []
        if lines_needed(t, size) >= 3:
            flags.append("3줄+")
        if mode == "gratitude" and len(t) > 15:
            flags.append("한 줄 넘칠 수 있음")
        if len(ws) == 1 and len(cs) > 1:
            flags.append("한 어절")
        if b - a < 0.7:
            flags.append(f"{b - a:.1f}초")
        warn += bool(flags)
        mark = "  ⚠ " + ", ".join(flags) if flags else ""
        print(f"  {a:6.2f}–{b:6.2f}  {t}{mark}")
    return warn


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("edit")
    ap.add_argument("--mode", default="all", choices=["all", *MODES])
    a = ap.parse_args()
    edit = Path(a.edit) if Path(a.edit).is_absolute() else ROOT / a.edit
    cap = json.loads((edit / "captions.json").read_text(encoding="utf-8"))
    words = cap["words"]
    if not words:
        sys.exit("[오류] captions.json 에 단어가 없어요.")
    total = {m: show(words, m) for m in (MODES if a.mode == "all" else [a.mode])}
    print("\n경고 수: " + ", ".join(f"{m} {n}" for m, n in total.items()))


if __name__ == "__main__":
    main()
