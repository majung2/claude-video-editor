"""[썸네일 담당 도구] 고른 장면 3개에 제목을 얹어 릴스 썸네일 후보 3장을 만든다.

장면 후보 고르기는 IT Reelsmaker의 poster.py(말 쉬는 순간, 눈 뜬 프레임)로 하고,
이 도구는 그 장면 위에 젠세리프 제목을 얹는 일만 한다.

    python3 tools/thumbs.py make edit/<id>        # edit/<id>/thumbs/spec.json → thumb_1~3.jpg + compare.jpg

spec.json 예시 (썸네일 담당이 작성):
    {"items": [
      {"src": "edit/<id>/final.mp4", "t": 12.4, "title": "오늘 제일\\n{감사했던} 순간", "sub": "감사일기 #12",
       "pos": "upper", "concept": "표정 클로즈업 + 감정 단어 강조"},
      {"src": "footage/<id>/broll/IMG_0123.jpg", "title": "...", "pos": "lower"},
      {"src": "edit/<id>/final.mp4", "t": 31.0, "title": "..."}
    ]}
    · title 의 \\n 은 줄바꿈, {중괄호} 는 강조색.  pos: upper | lower
    · src 가 영상이면 t(초) 필수, 사진이면 생략

안전 영역: 프로필 그리드는 가운데 1080×1440(3:4)만 보이고, 위 0~220·아래 1500~ 는 앱 UI.
→ 제목은 y 300~1440 안에만 놓는다. compare.jpg 에 3:4 영역을 점선으로 표시한다.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W, H = 1080, 1920
GRID_T, GRID_B = 240, 1680          # 3:4 그리드 크롭 (1080x1440)
SAFE_T, SAFE_B = 300, 1440
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv"}

FONT_CANDIDATES = [
    # 젠세리프 계열을 먼저 찾고, 없으면 시스템 명조/세리프
    "*ZenSerif*", "*Zen Serif*", "*젠세리프*", "*ZEN*Serif*",
    "AppleMyungjo*", "*NanumMyeongjo*Bold*", "*NanumMyeongjo*", "*NotoSerifKR*Bold*",
    "*NotoSerifCJK-Bold*", "*NotoSerifKR*", "*NotoSerifCJK*", "batang*",
]
FONT_DIRS = [ROOT / "assets" / "fonts", Path.home() / "Library" / "Fonts", Path("/Library/Fonts"),
             Path("/System/Library/Fonts"), Path("/System/Library/Fonts/Supplemental"),
             Path("/usr/share/fonts"), Path("C:/Windows/Fonts")]


def load_style() -> dict:
    p = ROOT / "config" / "style.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def find_font(style: dict) -> Path:
    if style.get("thumb_font") and Path(style["thumb_font"]).expanduser().exists():
        return Path(style["thumb_font"]).expanduser()
    for pat in FONT_CANDIDATES:
        for d in FONT_DIRS:
            if d.exists():
                hits = sorted(h for h in d.rglob(pat) if h.suffix.lower() in {".ttf", ".otf", ".ttc"})
                if hits:
                    return hits[0]
    sys.exit("[오류] 세리프 폰트를 못 찾았어요. 젠세리프 폰트 파일을 assets/fonts/ 에 넣거나 "
             "config/style.json 의 thumb_font 에 경로를 적어 주세요.")


def grab(src: Path, t: float | None, out: Path) -> Path:
    if src.suffix.lower() in VIDEO_EXT:
        if t is None:
            sys.exit(f"[오류] 영상 소스는 t(초)가 필요해요: {src}")
        r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}",
                            "-i", str(src), "-frames:v", "1", "-q:v", "2", str(out)])
        if r.returncode != 0 or not out.exists():
            sys.exit(f"[오류] 프레임 추출 실패: {src} @ {t}s")
        return out
    return src


def parse_runs(line: str) -> list[tuple[str, bool]]:
    runs, pos = [], 0
    for m in re.finditer(r"\{([^}]*)\}", line):
        if m.start() > pos:
            runs.append((line[pos:m.start()], False))
        runs.append((m.group(1), True))
        pos = m.end()
    if pos < len(line):
        runs.append((line[pos:], False))
    return runs


def render_one(item: dict, font_path: Path, style: dict, out: Path, tmp: Path, idx: int) -> None:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    src = (ROOT / item["src"]) if not Path(item["src"]).is_absolute() else Path(item["src"])
    if not src.exists():
        sys.exit(f"[오류] 소스가 없어요: {src}")
    frame = grab(src, item.get("t"), tmp / f"f{idx}.jpg")
    img = ImageOps.exif_transpose(Image.open(frame)).convert("RGB")
    fx = item.get("focus_x", 0.5)
    img = ImageOps.fit(img, (W, H), method=Image.LANCZOS, centering=(fx, 0.5))

    color = tuple(style.get("thumb_color", [255, 255, 255]))
    accent = tuple(style.get("thumb_accent", [255, 214, 120]))
    size = item.get("size", style.get("thumb_size", 112))
    lines = item["title"].replace("\\n", "\n").split("\n")
    font = ImageFont.truetype(str(font_path), size)
    sub_font = ImageFont.truetype(str(font_path), int(size * 0.42))
    line_h = int(size * 1.22)
    block_h = line_h * len(lines) + (int(size * 0.75) if item.get("sub") else 0)
    upper = item.get("pos", "upper") == "upper"
    y0 = SAFE_T + 20 if upper else SAFE_B - block_h

    # 글자 뒤 부드러운 그라데이션 (테두리·그림자 대신)
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    a, b = (0, y0 + block_h + 220) if upper else (y0 - 220, H)
    strength = item.get("shade", style.get("thumb_shade", 150))
    for y in range(max(0, a), min(H, b)):
        edge = (b - y) if upper else (y - a)
        sd.line([(0, y), (W, y)], fill=int(strength * min(1.0, edge / 220)))
    img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, shade)

    d = ImageDraw.Draw(img)
    margin = 90
    y = y0
    if item.get("sub") and upper:
        d.text((margin, y), item["sub"], font=sub_font, fill=accent)
        y += int(size * 0.75)
    for line in lines:
        x = margin
        for text, emph in parse_runs(line):
            d.text((x, y), text, font=font, fill=accent if emph else color)
            x += d.textlength(text, font=font)
        if x > W - margin:
            print(f"  ! 후보 {idx}: '{line}' 줄이 화면 폭을 넘어요 — 줄을 나누거나 size를 줄이세요")
        y += line_h
    if item.get("sub") and not upper:
        d.text((margin, y + 10), item["sub"], font=sub_font, fill=accent)
    img.save(out, quality=94)


def compare_sheet(paths: list[Path], items: list[dict], out: Path, font_path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont
    lf = ImageFont.truetype(str(font_path), 22)
    tw, th = 360, 640
    sheet = Image.new("RGB", (len(paths) * (tw + 20) + 20, th + 90), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    k = tw / W
    for i, p in enumerate(paths):
        im = Image.open(p).resize((tw, th))
        x = 20 + i * (tw + 20)
        sheet.paste(im, (x, 20))
        for yy in (GRID_T, GRID_B):                   # 3:4 그리드 크롭 표시
            for xx in range(0, tw, 12):
                d.line([(x + xx, 20 + yy * k), (x + xx + 6, 20 + yy * k)], fill=(0, 255, 140), width=2)
        d.text((x, th + 32), f"후보 {i+1}  {items[i].get('concept', '')[:24]}", fill=(255, 255, 255), font=lf)
    sheet.save(out, quality=90)


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] != "make":
        sys.exit(__doc__)
    edit = Path(sys.argv[2])
    edit = edit if edit.is_absolute() else ROOT / edit
    spec = json.loads((edit / "thumbs" / "spec.json").read_text(encoding="utf-8"))
    items = spec["items"]
    if len(items) != 3:
        print(f"  ! 후보가 {len(items)}개예요 (3개 권장)")
    style = load_style()
    font = find_font(style)
    print(f"폰트: {font.name}")
    outs = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, it in enumerate(items, 1):
            out = edit / "thumbs" / f"thumb_{i}.jpg"
            render_one(it, font, style, out, Path(tmp), i)
            outs.append(out)
            print(f"  저장: {out.relative_to(ROOT)}")
    compare_sheet(outs, items, edit / "thumbs" / "compare.jpg", font)
    print(f"비교 시트: {(edit / 'thumbs' / 'compare.jpg').relative_to(ROOT)}  (초록 점선 = 프로필 그리드 3:4 영역)")


if __name__ == "__main__":
    main()
