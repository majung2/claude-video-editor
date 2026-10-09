"""브랜드(영상 안) 폰트를 로컬 한글 폰트로 지정한다.

IT Reelsmaker 키트의 기본 폰트(Manrope·Inter)에는 한글이 없어서, 영상 안 글자는 로컬 폰트로 바꿔야 한다.
  · heading (화면 훅 문구 등 제목) — 젠세리프       : assets/fonts/ 의 *zen*serif* 파일
  · body    (자막)                 — 메모먼트 꾹꾹체 : assets/fonts/subtitle/ 의 파일

    python3 tools/fonts.py heading  <slug> [폰트파일]   제목·훅 문구 폰트 지정 (기본: 젠세리프)
    python3 tools/fonts.py subtitle <slug> [폰트파일]   자막 폰트 지정 (기본: assets/fonts/subtitle/)
    python3 tools/fonts.py                            (예비) Pretendard 를 assets/fonts/brand/ 에 내려받기
    python3 tools/fonts.py brand <slug>                (예비) 제목·본문을 모두 Pretendard 로

굵기가 하나뿐인 폰트는 같은 파일을 Regular·Medium·Bold·ExtraBold 이름으로 등록해, 키트가 굵게 요청해도
브라우저가 획을 억지로 두껍게(가짜 볼드) 만들지 않고 원래 모양 그대로 나오게 한다.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "1.3.9"
WEIGHTS = ["Medium", "SemiBold", "Bold", "ExtraBold"]


def fix_brand(slug: str) -> None:
    import json
    p = ROOT / "brands" / slug / "brand.json"
    if not p.exists():
        sys.exit(f"[오류] 브랜드가 없어요: {p}")
    b = json.loads(p.read_text(encoding="utf-8"))
    h = b.get("fonts", {}).get("heading", {})
    if h.get("source") != "local" or "Pretendard" not in h.get("family", ""):
        sys.exit("[오류] 브랜드 제목 폰트가 Pretendard 로컬 폰트가 아니에요. brand new … --scan assets/fonts/brand 로 만드세요.")
    b["fonts"]["body"] = dict(h)
    p.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{slug}: 제목·본문·자막 폰트 = Pretendard (로컬). 다음: brand export {slug} --remotion reels")


SUB_DIR = ROOT / "assets" / "fonts" / "subtitle"
# 키트 자막 모드가 요청하는 굵기: typewriter 500 · plate 700 · accent 800 (+ 400 기본)
SUB_WEIGHTS = {"Regular": 400, "Medium": 500, "Bold": 700, "ExtraBold": 800}


def default_files(role: str) -> list[Path]:
    exts = {".ttf", ".otf", ".woff", ".woff2"}
    if role == "body":
        return sorted(f for f in SUB_DIR.glob("*") if f.suffix.lower() in exts)
    d = ROOT / "assets" / "fonts"
    return sorted(f for f in d.glob("*") if f.suffix.lower() in exts
                  and "zen" in f.name.lower() and "serif" in f.name.lower())


def set_local_font(slug: str, font: str | None, role: str) -> None:
    """브랜드 폰트(role: heading=제목·훅 문구, body=자막)를 로컬 폰트 파일로 지정한다.
    파일에 굵기가 여러 개 있으면(…-Bold.ttf 등) 그대로 쓴다."""
    import json
    import re
    p = ROOT / "brands" / slug / "brand.json"
    if not p.exists():
        sys.exit(f"[오류] 브랜드가 없어요: {p}")
    if font:
        src = [Path(font).expanduser()]
    else:
        src = default_files(role)
    src = [f if f.is_absolute() else ROOT / f for f in src]
    if not src or not all(f.exists() for f in src):
        where = "assets/fonts/subtitle/" if role == "body" else "assets/fonts/ (젠세리프)"
        sys.exit(f"[오류] 폰트 파일이 없어요. {where} 에 넣거나 경로를 주세요.")
    family = re.sub(r"[-_ ]?(regular|medium|bold|extrabold|light|thin|black)$", "", src[0].stem, flags=re.I)
    family = re.sub(r"^TalkFile_", "", family)
    assets = p.parent / "assets"
    assets.mkdir(exist_ok=True)
    files = []
    if len(src) == 1:
        for wname in SUB_WEIGHTS:
            dst = assets / f"{family}-{wname}{src[0].suffix.lower()}"
            shutil.copy2(src[0], dst)
            files.append(f"assets/{dst.name}")
        weights = sorted(SUB_WEIGHTS.values())
    else:
        for f in src:
            shutil.copy2(f, assets / f.name)
            files.append(f"assets/{f.name}")
        weights = [400, 500, 700, 800]
    b = json.loads(p.read_text(encoding="utf-8"))
    b.setdefault("fonts", {})[role] = {"family": family, "source": "local", "weights": weights,
                                         "files": files, "italic": []}
    p.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    label = "자막(body)" if role == "body" else "제목·훅 문구(heading)"
    print(f"{slug}: {label} 폰트 = {family} (로컬, {len(files)}개 굵기로 등록). "
          f"다음: python3 tools/plug.py rm brand export {slug} --remotion reels")


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "brand":
        fix_brand(sys.argv[2])
        return
    if len(sys.argv) >= 3 and sys.argv[1] in ("subtitle", "heading"):
        set_local_font(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None,
                       "body" if sys.argv[1] == "subtitle" else "heading")
        return
    out = ROOT / "assets" / "fonts" / "brand"
    want = [out / f"Pretendard-{w}.woff2" for w in WEIGHTS]
    if all(p.exists() for p in want):
        print(f"있음: {out.relative_to(ROOT)}")
        return
    if not shutil.which("npm"):
        sys.exit("[오류] npm 이 없어요 (Node.js 설치 필요). 또는 Pretendard woff2/otf 파일을 직접 assets/fonts/brand/ 에 넣으세요.")
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        print(f"Pretendard {VERSION} 내려받는 중 (약 70MB, 필요한 4개만 남김) …")
        r = subprocess.run(["npm", "pack", f"pretendard@{VERSION}", "--silent"], cwd=tmp,
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"[오류] npm pack 실패:\n{r.stderr[-800:]}")
        tgz = next(Path(tmp).glob("pretendard-*.tgz"))
        with tarfile.open(tgz) as tf:
            for w in WEIGHTS:
                member = tf.getmember(f"package/dist/web/static/woff2/Pretendard-{w}.woff2")
                with tf.extractfile(member) as src, open(out / f"Pretendard-{w}.woff2", "wb") as dst:
                    shutil.copyfileobj(src, dst)
        lic = [m for m in tarfile.open(tgz).getnames() if m.endswith("LICENSE")]
        if lic:
            with tarfile.open(tgz) as tf, open(out / "LICENSE-Pretendard.txt", "wb") as dst:
                shutil.copyfileobj(tf.extractfile(lic[0]), dst)
    for p in want:
        print(f"저장: {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
