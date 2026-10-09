"""감독관용: 감사일기 영상 한 편(job)을 만들고 단계별 진행 상태를 기록한다.

    python3 tools/job.py new <id> --main <메인영상> [--broll <사진·영상 또는 폴더> ...]
    python3 tools/job.py status <id>
    python3 tools/job.py mark <id> <단계> <pending|running|done|failed|skipped> [--note 메모]

<id> 는 영상 이름 (예: 2026-10-09). 만들어지는 것:
    footage/<id>/main.<확장자>     카메라 보고 말하는 메인 영상
    footage/<id>/broll/           감사 제목별 사진·영상 (없어도 됨)
    edit/<id>/                    IT Reelsmaker 작업 폴더 (cut.json, captions.json, final.mp4 …)
    edit/<id>/pipeline.json       단계별 담당자·상태
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STEPS = [
    ("setup", "감독관 · 환경·브랜드·설정"),
    ("transcribe", "전사기"),
    ("hook", "후커"),
    ("cut", "컷편집 담당"),
    ("subtitle", "자막 담당"),          # ┐ 컷편집 후 병렬
    ("thumbnail", "썸네일 담당"),       # ┘
    ("broll", "화면연결 담당"),
    ("audio", "오디오 담당"),
    ("render", "감독관 · 렌더·검수·마스터"),
]
MEDIA = {".mp4", ".mov", ".m4v", ".mkv", ".jpg", ".jpeg", ".png", ".webp", ".heic"}


def heic_to_jpg(src: Path, dst_dir: Path) -> Path:
    out = dst_dir / (src.stem + ".jpg")
    try:
        from PIL import Image
        import pillow_heif  # type: ignore
        pillow_heif.register_heif_opener()
        Image.open(src).convert("RGB").save(out, quality=95)
        return out
    except Exception:
        pass
    if shutil.which("sips"):                                   # macOS 기본 도구
        subprocess.run(["sips", "-s", "format", "jpeg", str(src), "--out", str(out)],
                       capture_output=True)
        if out.exists():
            return out
    print(f"  ! HEIC 변환 실패, 원본만 복사: {src.name} (pip install pillow-heif 권장)")
    shutil.copy2(src, dst_dir / src.name)
    return dst_dir / src.name


def cmd_new(a) -> None:
    foot, edit = ROOT / "footage" / a.id, ROOT / "edit" / a.id
    if edit.exists() and (edit / "pipeline.json").exists():
        sys.exit(f"[오류] 이미 있는 영상 id예요: {a.id}")
    (foot / "broll").mkdir(parents=True, exist_ok=True)
    edit.mkdir(parents=True, exist_ok=True)
    main = Path(a.main).expanduser()
    if not main.exists():
        sys.exit(f"[오류] 메인 영상이 없어요: {main}")
    dst_main = foot / f"main{main.suffix}"
    shutil.copy2(main, dst_main)
    n = 0
    for b in a.broll or []:
        b = Path(b).expanduser()
        files = sorted(b.iterdir()) if b.is_dir() else [b]
        for f in files:
            if f.suffix.lower() not in MEDIA:
                continue
            if f.suffix.lower() == ".heic":
                heic_to_jpg(f, foot / "broll")
            else:
                shutil.copy2(f, foot / "broll" / f.name)
            n += 1
    state = {"id": a.id, "created": datetime.now().isoformat(timespec="seconds"),
             "main": str(dst_main.relative_to(ROOT)), "broll_dir": str((foot / "broll").relative_to(ROOT)),
             "broll_count": n,
             "steps": {k: {"owner": o, "status": "pending", "note": ""} for k, o in STEPS}}
    (edit / "pipeline.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"영상 준비 완료: {a.id}  메인 {dst_main.relative_to(ROOT)} / B-roll {n}개")


def load(id_: str) -> tuple[Path, dict]:
    p = ROOT / "edit" / id_ / "pipeline.json"
    if not p.exists():
        sys.exit(f"[오류] 없는 영상 id예요: {id_}")
    return p, json.loads(p.read_text(encoding="utf-8"))


def cmd_status(a) -> None:
    _, st = load(a.id)
    icon = {"pending": "·", "running": "▶", "done": "✓", "failed": "✗", "skipped": "–"}
    print(f"[{st['id']}] 메인 {st['main']} / B-roll {st['broll_count']}개")
    for k, v in st["steps"].items():
        note = f"  — {v['note']}" if v.get("note") else ""
        print(f"  {icon.get(v['status'], '?')} {k:<10} {v['owner']}{note}")


def cmd_mark(a) -> None:
    p, st = load(a.id)
    if a.step not in st["steps"]:
        sys.exit(f"[오류] 단계: {', '.join(st['steps'])}")
    st["steps"][a.step].update(status=a.status, note=a.note or "",
                               updated=datetime.now().isoformat(timespec="seconds"))
    p.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{a.step} → {a.status}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    n = sp.add_parser("new"); n.add_argument("id"); n.add_argument("--main", required=True)
    n.add_argument("--broll", nargs="*"); n.set_defaults(fn=cmd_new)
    s = sp.add_parser("status"); s.add_argument("id"); s.set_defaults(fn=cmd_status)
    m = sp.add_parser("mark"); m.add_argument("id"); m.add_argument("step")
    m.add_argument("status", choices=["pending", "running", "done", "failed", "skipped"])
    m.add_argument("--note"); m.set_defaults(fn=cmd_mark)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
