"""영상 자막·그래픽용 한글 폰트(Pretendard, SIL OFL 무료)를 받아 assets/fonts/brand/ 에 둔다.

IT Reelsmaker 키트의 기본 폰트(Manrope·Inter)에는 한글이 없어서, 브랜드를 만들 때 이 폴더를 --scan 으로 넘겨
로컬 폰트로 등록해야 자막이 제대로 나온다. (썸네일용 젠세리프는 따로 assets/fonts/ 에 직접 넣는다.)

    python3 tools/fonts.py                    → assets/fonts/brand/Pretendard-{Medium,SemiBold,Bold,ExtraBold}.woff2
    python3 tools/fonts.py brand <slug>       브랜드 제목·본문(자막) 폰트를 모두 Pretendard 로 맞춘다
                                              (brand.py new --scan 은 한 가족만 찾으면 본문을 한글 없는 Inter 로 둔다)

npm 레지스트리에서 받는다 (Node.js 필요). 이미 있으면 건너뛴다.
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


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "brand":
        fix_brand(sys.argv[2])
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
