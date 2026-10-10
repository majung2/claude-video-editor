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
    · align: left(기본) | center — 줄마다 가운데 정렬 (styles/<스타일>/thumb.json 의 thumb_align 으로 기본값 변경 가능)
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
    "*zen*serif*", "*젠*세리프*",
    "AppleMyungjo*", "*NanumMyeongjo*Bold*", "*NanumMyeongjo*", "*NotoSerifKR*Bold*",
    "*NotoSerifCJK-Bold*", "*NotoSerifKR*", "*NotoSerifCJK*", "batang*",
]
FONT_DIRS = [ROOT / "assets" / "fonts", Path.home() / "Library" / "Fonts", Path("/Library/Fonts"),
             Path("/System/Library/Fonts"), Path("/System/Library/Fonts/Supplemental"),
             Path("/usr/share/fonts"), Path("C:/Windows/Fonts")]


def style_of(edit: Path | None = None) -> str:
    """영상의 편집 스타일: edit/<id>/pipeline.json 의 "style" (job.py new --style), 없으면 gratitude."""
    if edit is not None:
        p = Path(edit) / "pipeline.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8")).get("style") or "gratitude"
    return "gratitude"


def load_style(style: str = "gratitude") -> dict:
    """썸네일 문구 모습: styles/<스타일>/thumb.json."""
    p = ROOT / "styles" / style / "thumb.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def find_font(style: dict) -> Path:
    if style.get("thumb_font") and Path(style["thumb_font"]).expanduser().exists():
        return Path(style["thumb_font"]).expanduser()
    import fnmatch
    for pat in FONT_CANDIDATES:
        for d in FONT_DIRS:
            if d.exists():
                # 파일 이름 대소문자 무시 (ZEN-SERIF-TTF-Regular.ttf, ZenSerif.otf 모두 찾음)
                hits = sorted(h for h in d.rglob("*") if h.suffix.lower() in {".ttf", ".otf", ".ttc"}
                              and fnmatch.fnmatch(h.name.lower(), pat.lower()))
                if hits:
                    return hits[0]
    sys.exit("[오류] 세리프 폰트를 못 찾았어요. 젠세리프 폰트 파일을 assets/fonts/ 에 넣거나 "
             "styles/<스타일>/thumb.json 의 thumb_font 에 경로를 적어 주세요.")


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

    # 글자는 마스크에 먼저 그린다: 본문(그라데이션) / 강조·sub(강조색) — 레퍼런스 썸네일 문구 모습
    plain = Image.new("L", (W, H), 0)
    emph_m = Image.new("L", (W, H), 0)
    dp, de = ImageDraw.Draw(plain), ImageDraw.Draw(emph_m)
    margin = 90
    y = y0
    x_max = margin
    if item.get("sub") and upper:
        de.text((margin, y), item["sub"], font=sub_font, fill=255)
        y += int(size * 0.75)
    center = item.get("align", style.get("thumb_align", "left")) == "center"
    x_min = W
    for line in lines:
        x = margin
        if center:
            lw = sum(dp.textlength(t, font=font) for t, _ in parse_runs(line))
            x = max(margin, (W - lw) / 2)
        x_min = min(x_min, x)
        for text, emph in parse_runs(line):
            (de if emph else dp).text((x, y), text, font=font, fill=255)
            x += dp.textlength(text, font=font)
        if x > W - margin:
            print(f"  ! 후보 {idx}: '{line}' 줄이 화면 폭을 넘어요 — 줄을 나누거나 size를 줄이세요")
        x_max = max(x_max, x)
        y += line_h
    if item.get("sub") and not upper:
        de.text((margin, y + 10), item["sub"], font=sub_font, fill=255)
    img = img.convert("RGBA")
    img.alpha_composite(text_layer(plain, emph_m, (min(margin, x_min) if not center else x_min, x_max), (y0, y0 + block_h), color, accent, style))
    img.convert("RGB").save(out, quality=94)


def _hex(c) -> tuple:
    if isinstance(c, str):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(c)


def wave_warp(layer, xr: tuple, amp: float, periods: float, phase: float):
    """글자 덩어리 폭(xr) 안에서 열마다 dy = -amp·sin(2π·periods·t + phase) 만큼 세로로 옮긴다 (양수 amp = 먼저 올라감)."""
    import math
    import numpy as np
    from PIL import Image
    a = np.asarray(layer).astype(np.float32)
    out = a.copy()
    x0, x1 = xr
    span = max(1.0, x1 - x0)
    for x in range(max(0, int(x0) - 40), min(W, int(x1) + 40)):
        t = min(1.0, max(0.0, (x - x0) / span))
        dy = -amp * math.sin(2 * math.pi * periods * t + phase)
        k = math.floor(dy)
        f = dy - k
        col = a[:, x]
        out[:, x] = (1 - f) * np.roll(col, k, axis=0) + f * np.roll(col, k + 1, axis=0)
    return Image.fromarray(out.round().clip(0, 255).astype(np.uint8), "RGBA")


def bevel(fill, mask, bev: dict):
    """엠보싱: 글자 가장자리 중 빛(왼쪽 위)을 향한 쪽은 밝게, 반대쪽(오른쪽 아래)은 살짝 어둡게."""
    import numpy as np
    from PIL import Image, ImageFilter
    a = np.asarray(mask.filter(ImageFilter.GaussianBlur(float(bev.get("blur", 2.5))))).astype(np.float32) / 255
    gy, gx = np.gradient(a)
    s = (gx + gy) / np.sqrt(2)  # 바깥쪽 법선이 왼쪽 위를 향하면 +
    m = np.abs(s).max() or 1.0
    s = np.clip(s / (m * 0.5), -1, 1)
    f = np.asarray(fill).astype(np.float32)
    k = float(bev["strength"])
    hi = np.clip(s, 0, 1)[..., None] * k
    lo = np.clip(-s, 0, 1)[..., None] * k * float(bev.get("dark", 0.45))
    out = f + hi * (255 - f) - lo * f
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGB")


def text_layer(plain, emph, xr: tuple, yr: tuple, color, accent, style: dict):
    """레퍼런스 썸네일 문구 모습 (style.json): 가로 파스텔 그라데이션(thumb_gradient) · 아주 옅은 그림자(thumb_shadow)
    · 오른쪽이 살짝 올라가게 기울임(thumb_tilt 도). 그라데이션이 비어 있으면 thumb_color 단색."""
    from PIL import Image, ImageChops, ImageFilter
    stops = [_hex(c) for c in style.get("thumb_gradient", [])]
    fill = Image.new("RGB", (W, H), color)
    if len(stops) >= 2:
        x0, x1 = xr
        span = max(1, x1 - x0)
        row = Image.new("RGB", (W, 1))
        for x in range(W):
            t = min(1.0, max(0.0, (x - x0) / span)) * (len(stops) - 1)
            k = min(int(t), len(stops) - 2)
            f = t - k
            row.putpixel((x, 0), tuple(round(a + (b - a) * f) for a, b in zip(stops[k], stops[k + 1])))
        fill = row.resize((W, H), Image.NEAREST)
    fill.paste(Image.new("RGB", (W, H), accent), (0, 0), emph)
    mask = ImageChops.lighter(plain, emph)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh = style.get("thumb_shadow", {})
    if sh.get("alpha", 0) > 0:
        a = mask.filter(ImageFilter.GaussianBlur(sh.get("blur", 6))).point(lambda v: int(v * sh["alpha"]))
        shadow = Image.new("RGBA", (W, H), tuple(_hex(sh.get("color", "#000000"))) + (0,))
        shadow.putalpha(a)
        layer.alpha_composite(shadow, (int(sh.get("dx", 3)), int(sh.get("dy", 4))))
    bev = style.get("thumb_bevel", {})
    if bev.get("strength", 0) > 0:
        fill = bevel(fill, mask, bev)
        # 두께: 글자를 살짝 어둡게 해서 오른쪽 아래로 depth px 만큼 쌓는다 (도톰하게 튀어나온 느낌)
        dark = fill.point(lambda v: int(v * float(bev.get("side", 0.82)))).convert("RGBA")
        dark.putalpha(mask)
        for k in range(int(bev.get("depth", 2)), 0, -1):
            layer.alpha_composite(dark, (k, k))
    text = fill.convert("RGBA")
    text.putalpha(mask)
    layer.alpha_composite(text)

    wave = style.get("thumb_wave", {})
    if wave.get("amp", 0):  # 글자 줄이 물결처럼: 세로 위치를 사인 곡선으로 (세로 픽셀 단위, 소수점까지 부드럽게)
        layer = wave_warp(layer, xr, float(wave["amp"]), float(wave.get("periods", 1.0)), float(wave.get("phase", 0.0)))
    tilt = float(style.get("thumb_tilt", 0))
    if tilt:  # 양수 = 반시계 = 오른쪽이 올라감. 글자 덩어리 가운데를 축으로
        cx, cy = (xr[0] + xr[1]) / 2, (yr[0] + yr[1]) / 2
        layer = layer.rotate(tilt, resample=Image.BICUBIC, center=(cx, cy))
    return layer


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
    style = load_style(spec.get("style") or style_of(edit))
    font = find_font(style)
    print(f"폰트: {font.name}")
    outs = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, it in enumerate(items, 1):
            out = edit / "thumbs" / f"thumb_{i}.jpg"
            render_one(it, font, style, out, Path(tmp), i)
            outs.append(out)
            print(f"  저장: {out}")
    compare_sheet(outs, items, edit / "thumbs" / "compare.jpg", font)
    print(f"비교 시트: {edit / 'thumbs' / 'compare.jpg'}  (초록 점선 = 프로필 그리드 3:4 영역)")


if __name__ == "__main__":
    main()
