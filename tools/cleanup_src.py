"""[최종 컨펌 뒤] 아이클라우드 촬영본 폴더에서 그 영상에 쓴 원본을 지운다 (모든 편집 스타일 공용, 사용자 결정 2026-10-22).

    python3 tools/cleanup_src.py <id> --src <촬영본 폴더>            # 지울 목록만 보여 줌 (기본, 아무것도 안 지움)
    python3 tools/cleanup_src.py <id> --src <촬영본 폴더> --yes      # 실제로 삭제
    python3 tools/cleanup_src.py <id> --src <촬영본 폴더> --also 파일명 ... [--yes]
                                                                    # 툴킷에 사본이 없는 원본(나중에 올린 사진 등)을
                                                                    #   footage/<id>/broll/ 로 먼저 복사한 뒤 함께 지움

안전 장치
- 툴킷 footage/<id>/ 에 같은 크기의 사본(main.*, broll/*)이 있는 원본만 지운다 → 지워도 원본은 툴킷에 남는다.
- 사본이 없는 파일은 "사본 없음"으로만 보여 주고 지우지 않는다 (--also 로 지정하면 복사 후 삭제).
- 결과물 폴더·다른 날짜의 원본은 건드리지 않는다. 파일 이름은 NFC/NFD 와 상관없이 맞춘다.
- 기기 연결 셸에서는 삭제가 기본으로 막혀 있다 → 감독관이 먼저 원본 폴더(크리에이터) 삭제 권한을 요청한다.
- 지운 목록은 edit/<id>/cleanup.json 에 남긴다.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEDIA = {".mp4", ".mov", ".m4v", ".mkv", ".jpg", ".jpeg", ".png", ".webp", ".heic"}


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--src", required=True, help="아이클라우드 원본 폴더 (예: 크리에이터/감사일기/촬영본)")
    ap.add_argument("--also", nargs="*", default=[], help="툴킷에 사본이 없지만 이번 영상에 쓴 원본 파일 이름")
    ap.add_argument("--yes", action="store_true", help="실제로 삭제 (없으면 목록만)")
    a = ap.parse_args()

    foot = ROOT / "footage" / a.id
    if not foot.is_dir():
        sys.exit(f"[오류] footage/{a.id} 가 없어요")
    src = Path(a.src).expanduser()
    if not src.is_dir():
        sys.exit(f"[오류] 원본 폴더가 없어요: {src}")

    copies = [p for p in [*foot.glob("main.*"), *(foot / "broll").glob("*")] if p.is_file()]
    by_name = {nfc(p.name): p for p in copies}
    sizes = {}
    for p in copies:
        sizes.setdefault(p.stat().st_size, []).append(p)
    pipe = ROOT / "edit" / a.id / "pipeline.json"
    recorded = set()
    if pipe.exists():
        recorded = {nfc(Path(s).name) for s in json.loads(pipe.read_text(encoding="utf-8")).get("sources", [])}
    also = {nfc(x) for x in a.also}

    plan = []  # (원본, 사본 or None, 이유)
    for f in sorted(src.iterdir(), key=lambda p: nfc(p.name)):
        if not f.is_file() or f.suffix.lower() not in MEDIA:
            continue
        n, size = nfc(f.name), f.stat().st_size
        same = by_name.get(n) if by_name.get(n) and by_name[n].stat().st_size == size else None
        if same is None and size in sizes:
            same = sizes[size][0]
        if same is None and f.suffix.lower() == ".heic" and nfc(f.stem + ".jpg") in by_name:
            same = by_name[nfc(f.stem + ".jpg")]          # job.py 가 HEIC 를 jpg 로 바꿔 둔 경우
        if same is not None:
            plan.append((f, same, "사본 있음"))
        elif n in also:
            plan.append((f, None, "복사 후 삭제(--also)"))
        elif n in recorded:
            plan.append((f, None, "사본 없음 — 지우지 않음 (--also 로 지정하면 복사 후 삭제)"))

    if not plan:
        print("지울 원본이 없어요 (이 영상의 사본과 맞는 파일이 촬영본 폴더에 없음)")
        return
    total = 0
    for f, c, why in plan:
        mb = f.stat().st_size / 1e6
        total += mb if why != "사본 없음 — 지우지 않음 (--also 로 지정하면 복사 후 삭제)" else 0
        print(f"  {'삭제' if not why.startswith('사본 없음') else '보존'}  {nfc(f.name):48s} {mb:8.1f}MB  {why}" + (f" → {c.relative_to(ROOT)}" if c else ""))
    others = [nfc(p.name) for p in src.iterdir() if p.is_file() and p.suffix.lower() in MEDIA and p not in [x[0] for x in plan]]
    if others:
        print(f"  (이 영상과 무관해서 그대로 둘 파일 {len(others)}개: {', '.join(others[:8])}{' …' if len(others) > 8 else ''})")
    print(f"합계 {total:.0f}MB")
    if not a.yes:
        print("목록만 보여 줬어요. 실제로 지우려면 --yes")
        return

    done = []
    for f, c, why in plan:
        if why.startswith("사본 없음"):
            continue
        if c is None:  # --also: 툴킷으로 먼저 복사
            (foot / "broll").mkdir(parents=True, exist_ok=True)
            c = foot / "broll" / nfc(f.name)
            shutil.copy2(f, c)
            if c.stat().st_size != f.stat().st_size:
                print(f"  ! 복사 크기가 달라 지우지 않음: {nfc(f.name)}")
                continue
        os.remove(f)
        done.append({"file": nfc(f.name), "copy": str(c.relative_to(ROOT)), "bytes": c.stat().st_size})
        print(f"  삭제함  {nfc(f.name)}")
    log = ROOT / "edit" / a.id / "cleanup.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps({"when": datetime.now().isoformat(timespec="seconds"), "src": str(src), "deleted": done},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"삭제 {len(done)}개 → 기록 {log.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
